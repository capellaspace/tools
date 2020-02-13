"""capella.scripts.cli."""

import aiohttp
import asyncio
import async_timeout
import json
import logging
import os

import click
from shapely.geometry import shape
import struct

capella_url = 'https://api.data.capellaspace.com'
token = 'token'
data_collections = 'catalog/collections'
catsearch = 'catalog/stac/search'
orders = 'orders'
download = 'download'

chunk_size = 1024

logger = logging.getLogger(__name__)


def get_parameters(ctx):
    return (ctx.obj['username'], ctx.obj['password'],
            ctx.obj['collection'], ctx.obj['area'], ctx.obj['limit'])


@click.group(short_help="Capella Space related utilities.")
@click.option('--area', type=click.File('r'), default=None, help="A geojson\
     file containing request area and filter")
@click.option('--collection', default=None, help="If area is not specified then\
     the name of a collection to retrieve")
@click.option('--credentials', default=None)
@click.option('--limit', type=int, default=10, help="Specify maximum number of\
     results to return.")
@click.option('--verbose', '-v', is_flag=True, help="Verbose output")
@click.pass_context
def capella(ctx, area, collection, credentials, limit, verbose):
    """Capella Space.
    """
    if verbose:
        logger.setLevel(logging.INFO)

    if area is None and collection is None:
        click.Abort('One of "collection" or "area" is required.')

    ctx.ensure_object(dict)

    if credentials and not os.path.exists(credentials):
        click.Abort(f"Credentials path: {credentials} does not exist.")
    elif credentials:
        with open(credentials) as f:
            data = json.load(f)
            ctx.obj['username'] = data['username']
            ctx.obj['password'] = data['password']
    else:
        ctx.obj['username'] = None
        ctx.obj['password'] = None

    ctx.obj['collection'] = collection
    ctx.obj['limit'] = limit

    if area:
        geojson = json.load(area)
        ctx.obj['area'] = geojson
    else:
        ctx.obj['area'] = area


@capella.command(short_help="Query Capella STAC catalog.")
@click.pass_context
def query(ctx):
    username, password, collection, area, limit = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    if not (area or collection):
        click.Abort('Require either an area or a collection name to query the\
             catalog.')

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_query(area, collection, limit, auth))
    print(json.dumps(result))


@capella.command(short_help="Obtain authentication headers (useful for debug).")
@click.pass_context
def auth_headers(ctx):
    username, password, collection, area, limit = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_auth_headers(auth))
    print(json.dumps(result))


@capella.command(short_help="Query Capella for available collections.")
@click.pass_context
def collections(ctx):
    username, password, collection, area, limit = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_collections(auth))
    print(json.dumps(result))


@capella.command(short_help="Order Capella data.")
@click.argument('output', type=click.Path(exists=True))
@click.option('--requests', type=int, default=10, help="Specify maximum number\
     of concurrent requests.")
@click.pass_context
def order(ctx, output, requests):
    """Order Capella Space data
    
    Parameters

    output: The output directory (must exist) for the downloaded data
    """
    username, password, collection, area, limit = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    asyncio.run(get_data(area, collection, output, limit, requests, auth))


async def get_query(geojson, collection, limit, auth):
    filters = {
        'limit': limit
    }

    if not (collection and geojson):
        hdrs = await get_auth_headers(auth)

        if collection:
            async with aiohttp.ClientSession(headers=hdrs) as session:
                async with session.get(
                                    f"{capella_url}/{data_collections}/"
                                    f"{collection}/items?limit={limit}"
                                    ) as response:
                    status = response.status
                    logger.info(f"STAC response code {status}")
                    result = await response.json()
                    logger.info(f"STAC: {result}")
                    return result

        if geojson:
            if 'properties' in geojson:
                props = geojson['properties']
                for k, v in props.items():
                    filters[k] = v

            if 'geometry' in geojson:
                g = shape(geojson['geometry'])
                filters['bbox'] = list(g.bounds)

            logger.info(f"Filter: {filters}")

            async with aiohttp.ClientSession(headers=hdrs) as session:
                async with session.post(
                                        f"{capella_url}/{catsearch}",
                                        json=filters) as response:
                    status = response.status
                    logger.info(f"STAC response code {status}")
                    result = await response.json()
                    logger.info(f"STAC: {result}")
                    return result
    else:
        click.Abort('Can only specify one of collection or geojson area.')


async def get_collections(auth):
    hdrs = await get_auth_headers(auth)
    async with aiohttp.ClientSession(headers=hdrs) as session:
        async with session.get(f"{capella_url}/{data_collections}") as response:
            status = response.status
            logger.info(f"Collections response code {status}")
            result = await response.json()
            logger.info(f"Collections: {result}")
            return result


async def get_auth_headers(auth):
    logger.info("Requesting auth token.")
    async with aiohttp.ClientSession(auth=auth) as client:
        async with client.post(f"{capella_url}/{token}") as response:
            status = response.status
            logger.info(f"Received response with status {status}")

            if status == 201:
                body = await response.json()
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/geo+json',
                    'Authorization':'Bearer ' + body['accessToken']
                    }
                return headers

            if status == 401:
                click.Abort('Username and Password is incorrect.')

            if status == 403:
                click.Abort('Too many failed login attempts. Try again later.')


async def get_url(url, output, session):
    filename = url[url.rfind("/")+1:]
    truncname = filename.split('?', 1)[0] 

    async with async_timeout.timeout(120):
        async with session.get(url) as response:
            with open(os.path.join(output, truncname), 'wb') as f:
                async for data in response.content.iter_chunked(chunk_size):
                    f.write(data)
                logger.info(f"Retrieved {truncname}")


async def parallel_fetch(urls, output, request_limit):
    connector = aiohttp.TCPConnector(limit=request_limit)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [get_url(url, output, session) for url in urls]
        return await asyncio.gather(*tasks)


async def get_data(geojson, collection, output, data_limit, request_limit,
                    auth=None):
    hdrs = await get_auth_headers(auth)
    async with aiohttp.ClientSession(headers=hdrs) as session:
        result = await get_query(geojson, collection, data_limit, auth)
        # make an order
        features = result["features"]
        granules = []

        for f in features:
            item = {'CollectionId': f['collection'], 'GranuleId': f['id']}
            granules.append(item)

        order = {'Items': granules}

        logger.info(f"Order: {order}")

        # Place the order and inspect the result
        async with session.post(
                f"{capella_url}/{orders}", json=order) as response:
            logger.info(f"Order response code: {response.status}")
            result = await response.json()
            logger.info(f"Order: {result}")

            # Get the STAC records with the signed URLs using the /download endpoint
            async with session.get(f"{capella_url}/{orders}/{result['orderId']}"
                                   f"/{download}") as response:
                logger.info(f"Download response code: {response.status}")
                result = await response.json()
                logger.info(f"Download: {result}")

                urls = []

                for f in result:
                    polarizations = f['properties']['sar:polarization']
                    for p in polarizations:
                        urls.append(f['assets'][p]['href'])

                logger.info(urls)

                if len(urls) > 0:
                    await parallel_fetch(urls, output, request_limit)
                else:
                    click.abort('No matching records found.')


def ask_for_creds():
    username = click.prompt('What is your username?')
    password = click.prompt('What is your password?', hide_input=True)
    return username, password


if __name__ == '__main__':
    capella(obj={})
