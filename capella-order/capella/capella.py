"""capella.capella."""

import aiohttp
import asyncio
import async_timeout
import logging
import os

from shapely.geometry import shape
import struct


logger = logging.getLogger(__name__)


capella_url = 'https://api.data.capellaspace.com'
token = 'token'
data_collections = 'catalog/collections'
catsearch = 'catalog/stac/search'
orders = 'orders'
download = 'download'

chunk_size = 1024


async def get_query(geojson, collection, limit, page, auth):
    if not (collection and geojson):
        hdrs = await get_auth_headers(auth)

        if collection:
            async with aiohttp.ClientSession(headers=hdrs) as session:
                async with session.get(
                                    f"{capella_url}/{data_collections}/"
                                    f"{collection}/items?limit={limit}"
                                    f"&page={page}"
                                    ) as response:
                    status = response.status
                    logger.info(f"STAC response code {status}")
                    result = await response.json()
                    logger.info(f"STAC: {result}")
                    return result

        if geojson:
            filters = {
                'limit': limit,
                'page': page
            }

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


async def get_collections(auth, limit, page):
    hdrs = await get_auth_headers(auth)
    async with aiohttp.ClientSession(headers=hdrs) as session:
        async with session.get(f"{capella_url}/{data_collections}"
                               f"?limit={limit}&page={page}"
              ) as response:
            status = response.status
            logger.info(f"Collections response code {status}")
            result = await response.json()
            logger.info(f"Collections: {result}")
            return result


async def get_auth_headers(auth):
    if 'Authorization' in auth:
      if auth['Authorization'].startswith('Bearer'):
        return auth

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
                    'Connection': 'close',
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
    async with aiohttp.ClientSession(
                            connector=connector,
                            headers={'Connection': 'close'}) as session:
        tasks = [get_url(url, output, session) for url in urls]
        return await asyncio.gather(*tasks)


async def get_data(geojson, collection, output, data_limit, page, request_limit,
                    auth=None):
    hdrs = await get_auth_headers(auth)
    async with aiohttp.ClientSession(headers=hdrs) as session:
        result = await get_query(geojson, collection, data_limit, page, auth)
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
            order_result = await response.json()
            logger.info(f"Order: {order_result}")

            # Get the STAC records with the signed URLs using the /download endpoint
            async with session.get(f"{capella_url}/{orders}"
                                   f"/{order_result['orderId']}"
                                   f"/{download}") as response:
                logger.info(f"Download response code: {response.status}")
                download_result = await response.json()
                logger.info(f"Download: {download_result}")

                urls = []

                for f in download_result:
                    polarizations = f['properties']['sar:polarizations']
                    for p in polarizations:
                        urls.append(f['assets'][p]['href'])

                logger.info(urls)

                if len(urls) > 0:
                    await parallel_fetch(urls, output, request_limit)
                else:
                    click.abort('No matching records found.')
        # return query metadata
        return result
