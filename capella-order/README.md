# Capella Space Order plugin

This is a Python 3.7 plugin in to [Rasterio](https://github.com/mapbox/rasterio).

## Installation

```
$ git clone https://github.com/capellaspace/tools.git
$ cd tools
$ pip install -U pip
$ pip install -e .
```

## CLI

Usage: rio capella-order [OPTIONS] AREA OUTPUT

  Order Capella Space data

  Parameters

  area : A geojson file containing request area and filter output: The
  output directory (must exist) for the downloaded data

Options:
  --credentials TEXT
  --limit INTEGER      Specify maximum number of results to return.
  --requests INTEGER   Specify maximum number of concurrent requests.
  --polarization TEXT  Polarization requested e.g. HH.
  -v, --verbose        Verbose output
  --help               Show this message and exit.

### Examples

Create an `area.json` file with the following contents;

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
    "startTime" : "2019-08-01T00:00:00Z",
    "endTime" : "2019-12-31T12:31:12Z",
    "sort":  [{"field": "dtr:start_datetime"}]
  }
}
```

and an `output` directory and execute;

`rio capella-order area.json output -v`

Credentials can also be stored in a JSON file of the form

```
{
  "username": user,
  "password": pswd
}
```
