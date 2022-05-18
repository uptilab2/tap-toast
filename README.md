
# tap-toast

Tap for [Client Data](https://pos.toasttab.com/).


## Usage

### Create config file

You can get all of the below from talking to a sales representative at Client (totally obnoxious, I know).

```
{
  "client_id": "***",
  "client_secret": "***",
  "location_guid": "***",
  "modifiedDate": "2018-11-12T11:00:30+00:00"
}
```

The `location_guid` is the primary id for the restaurant, which is necessary to access the API.

The `modifiedDate` is just the date you want the sync to begin. You can select this yourself.

### Discovery mode

This command returns a JSON that describes the schema of each table.

```
$ tap-toast --config config.json --discover
```

To save this to `catalog.json`:

```
$ tap-toast --config config.json --discover > catalog.json
```

### Field selection

You can tell the tap to extract specific fields by editing `catalog.json` to make selections. Note the top-level `selected` attribute, as well as the `selected` attribute nested under each property.

```
{
  "selected": "true",
  "properties": {
    "likes_getting_petted": {
      "selected": "true",
      "inclusion": "available",
      "type": [
        "null",
        "boolean"
      ]
    },
    "name": {
      "selected": "true",
      "maxLength": 255,
      "inclusion": "available",
      "type": [
        "null",
        "string"
      ]
    },
    "id": {
      "selected": "true",
      "minimum": -2147483648,
      "inclusion": "automatic",
      "maximum": 2147483647,
      "type": [
        "null",
        "integer"
      ]
    }
  },
  "type": "object"
}
```

### Sync Mode

With an annotated `catalog.json`, the tap can be invoked in sync mode:

```
$ tap-toast --config config.json --catalog catalog.json
```

Messages are written to standard output following the Singer specification. The resultant stream of JSON data can be consumed by a Singer target.
