"""capella.scripts.cli."""

from capella import *

import click

import asyncio
import aiohttp
import json
import logging
import os
import warnings


logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")


def get_parameters(ctx):
    return (ctx.obj['username'], ctx.obj['password'],
            ctx.obj['collection'], ctx.obj['area'], ctx.obj['limit'],
            ctx.obj['page'])


@click.group(short_help="Capella Space related utilities.")
@click.option('--area', type=click.File('r'), default=None, help="A geojson\
     file containing request area and filter")
@click.option('--collection', default=None, help="If area is not specified then\
     the name of a collection to retrieve")
@click.option('--credentials', default=None)
@click.option('--limit', type=int, default=10, help="Specify maximum number of\
     results to return.")
@click.option('--page', type=int, default=1, help="Specify page to return.")
@click.option('--verbose', '-v', is_flag=True, help="Verbose output")
@click.pass_context
def capella(ctx, area, collection, credentials, limit, page, verbose):
    """Capella Space.
    """
    if verbose:
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for l in loggers:
            l.setLevel(logging.INFO)

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
    ctx.obj['page'] = page

    if area:
        geojson = json.load(area)
        ctx.obj['area'] = geojson
    else:
        ctx.obj['area'] = area


@capella.command(short_help="Query Capella STAC catalog.")
@click.pass_context
def query(ctx):
    username, password, collection, area, limit, page = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    if not (area or collection):
        click.Abort('Require either an area or a collection name to query the\
             catalog.')

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_query(area, collection, limit, page, auth))
    print(json.dumps(result))


@capella.command(short_help="Obtain authentication headers (useful for debug).")
@click.pass_context
def auth_headers(ctx):
    username, password, _, _, _, _ = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_auth_headers(auth))
    print(json.dumps(result))


@capella.command(short_help="Query Capella for available collections.")
@click.pass_context
def collections(ctx):
    username, password, collection, _, limit, page = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_collections(auth, limit, page))
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
    username, password, collection, area, limit, page = get_parameters(ctx)

    # prompts for username go here so that the 'help' option still works
    if not username:
        username, password = ask_for_creds()

    auth = aiohttp.BasicAuth(login=username, password=password)

    result = asyncio.run(get_data(area, collection, output, limit,
                            page, requests, auth))
    print(json.dumps(result))


def ask_for_creds():
    username = click.prompt('What is your username?')
    password = click.prompt('What is your password?', hide_input=True)
    return username, password


if __name__ == '__main__':
    capella(obj={})
