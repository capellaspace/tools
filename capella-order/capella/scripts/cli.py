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
catsearch = 'catalog/stac/search'
orders = 'orders'
download = 'download'

chunk_size = 1024

logger = logging.getLogger(__name__)

@click.group(short_help="Capella Space related utilities.")
@click.pass_context
def capella():
    """Capella subcommands."""
    pass


@capella.command(short_help="Order Capella data.")
@click.argument('area', type=click.File('r'))
@click.argument('output', type=click.Path(exists=True))
@click.option('--credentials', default=None)
@click.option('--limit', type=int, default=10, help="Specify maximum number of results to return.")
@click.option('--requests', type=int, default=10, help="Specify maximum number of concurrent requests.")
@click.option('--polarization', default='HH', help="Polarization requested e.g. HH.")
@click.option('--verbose', '-v', is_flag=True, help="Verbose output")
@click.pass_context
def capella_order(ctx, area, output, credentials, limit, requests, polarization, verbose):
    """Order Capella Space data
    
    Parameters

    area : A geojson file containing request area and filter
    output: The output directory (must exist) for the downloaded data
    """

    if verbose:
        logger.setLevel(logging.INFO)

    if credentials is None:
        username, password = ask_for_creds()
    elif not os.path.exists(credentials):
        click.Abort(f"Credentials path: {credentials} does not exist.")
    else:
        with open(credentials) as f:
            data = json.load(f)
            username = data['username']
            password = data['password']

    geojson = json.load(area)

    auth = aiohttp.BasicAuth(login=username, password=password)

    asyncio.run(get_data(geojson, output, limit, requests, polarization, auth))


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


async def get_data(geojson, output, data_limit, request_limit, polarization, auth=None):
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
                async with aiohttp.ClientSession(headers=headers) as session:
                    props = geojson['properties']
                    g = shape(geojson['geometry'])

                    filters = {
                        'bbox': list(g.bounds),
                        'time': f"{props['startTime']}/{props['endTime']}",
                        'limit': data_limit,
                        'sort' : props['sort']
                    }
                    logger.info(f"Filter: {filters}")

                    async with session.post(
                                            f"{capella_url}/{catsearch}",
                                            json=filters) as response:
                        status = response.status
                        logger.info(f"STAC response code {status}")
                        result = await response.json()
                        logger.info(f"STAC: {result}")

                        # make an order
                        features = result["features"]
                        granules = []

                        for f in features:
                            item = {'CollectionId': f['collection'], 'GranuleId': f['id']}
                            granules.append(item)

                        order = {'Items': granules}

                        logger.info(f"Order: {order}")

                        # Place the order and inspect the result
                        async with session.post(f"{capella_url}/{orders}", json=order) as response:
                            logger.info(f"Order response code: {response.status}")
                            result = await response.json()
                            logger.info(f"Order: {result}")

                            # Get the STAC records with the signed URLs using the /download endpoint
                            async with session.get(f"{capella_url}/{orders}/{result['orderId']}/{download}") as response:
                                logger.info(f"Download response code: {response.status}")
                                result = await response.json()
                                logger.info(f"Download: {result}")

                                urls = []
                                for f in result:
                                    if polarization in f['assets']:
                                        urls.append(f['assets'][polarization]['href'])

                                logger.info(urls)

                                if len(urls) > 0:
                                    await parallel_fetch(urls, output, request_limit)
                                else:
                                    click.abort('No matching records found.')

            if status == 401:
                click.Abort('Username and Password is incorrect.')

            if status == 403:
                click.Abort('Too many failed login attempts. Try again later.')


def ask_for_creds():
    username = click.prompt('What is your username?')
    password = click.prompt('What is your password?', hide_input=True)
    return username, password
