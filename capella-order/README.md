# Capella Space Order plugin

This is a Python 3.7 plugin in to [Rasterio](https://github.com/mapbox/rasterio).

It is recommended to install [jq](https://stedolan.github.io/jq/) as many of the examples use this tool.

## Installation

```
$ git clone https://github.com/capellaspace/tools.git
$ cd tools
$ cd capella-order
$ pip install -U pip
$ python setup.py install
```

## CLI

```
Usage: rio capella [OPTIONS] COMMAND [ARGS]...

  Capella Space.

Options:
  --area FILENAME     A geojson file containing request area and filter
  --collection TEXT   If area is not specified then the name of a collection
                      to retrieve
  --credentials TEXT
  --limit INTEGER     Specify maximum number of results to return.
  -v, --verbose       Verbose output
  --help              Show this message and exit.

Commands:
  auth-headers  Obtain authentication headers (useful for debug).
  collections  Query Capella for available collections.
  order        Order Capella data.
  query        Query Capella STAC catalog.

```
```
Usage: rio capella auth-headers [OPTIONS]

Options:
  --help  Show this message and exit.
```
```
Usage: rio capella collections [OPTIONS]

Options:
  --help  Show this message and exit.
```
```
Usage: rio capella query [OPTIONS]

Options:
  --help  Show this message and exit.
```
```
Usage: rio capella order [OPTIONS] OUTPUT

  Order Capella Space data

  Parameters

  output: The output directory (must exist) for the downloaded data

Options:
  --requests INTEGER  Specify maximum number of concurrent requests.
  --help              Show this message and exit.
```

### Examples

Credentials can also be stored in a JSON file of the form

```
{
  "username": user,
  "password": pswd
}
```

1. Query for available collections

`rio capella --credentials credentials.json collections | jq '.collections[].id'`

2. Query by collection

`rio capella --credentials credentials.json --collection mycollection query | jq '.'`

3. Create an `area.json` file with the following contents;

```
{
  "type": "Feature",
  "geometry": {
     "type": "Polygon",
     "coordinates": [[
        [4.033856201171875, 51.04426252720166],
        [4.968939208984375, 51.04426252720166],
        [4.968939208984375, 52.560346153985355],
        [4.033856201171875, 52.560346153985355],
        [4.033856201171875, 51.04426252720166]
        ]]
  },
  "properties": {
    "sort":  [{"field": "dtr:start_datetime"}]
  }
}
```

and an `output` directory and execute;

`rio capella --credentials credentials.json --area area.json order output`

4. Obtain authentication headers

`rio capella --credentials credentials.json auth-headers`