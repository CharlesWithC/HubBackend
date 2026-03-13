# Delivery Log

The most crucial part of the drivers hub is handling delivery logs, where third-party trackers submit data through webhook endpoint to drivers hub, and drivers hub processes and stores the data.

Due to historical reasons, "job" is called "delivery log" / "dlog" in drivers hub. This also includes cancelled jobs with possibly negative revenue (i.e. penalty).

## Tracker

All job trackers are third-party software installed as plugins along the game. This project does not provide a tracker software as it is out-of-scope.

Delivery logs are submitted to drivers hub through the `/{tracker}/update` endpoint. This endpoint should only be used by external trackers. Three popular trackers are supported: Trucky, UniTracker, TrackSim.

Navio by TruckSpace was supported when it was active, but following the shutdown of the service, the data intake endpoint was removed while existing data was preserved. Navio's data format was also preserved as the only storage format because it was deemed to be the most well-structured format.

Data from currently-supported trackers will be converted into Navio's format for storage. Note that TrackSim's data format is identical to Navio's, and thus TrackSim was a drop-in replacement with no data conversion functionality.

*Fun fact: I was originally part of the founding team of TrackSim when Navio shut down. We decided to preserve the format for easy replacement - and we even preserved the design and language choice (Rust / Tauri) for the installation wizard. Unfortunately I was removed from the team due to conflict of interests on the drivers hub project.*

Custom tracker is supported with data intake endpoint `/custom/update`. It must use Navio's data format as there is no built-in conversion functionality. You may create an external plugin to handle data conversion if you use an unsupported tracker.

When data is received at the webhook endpoint, the drivers hub will try to validate the signature using the webhook secret, as well as the IP where the request is originated, if applicable. More information can be found in `trackers` attribute in [/docs/config.jsonc](/docs/config.jsonc).

## Route

TrackSim and UniTracker provide telemetry data that reflects the route the player took when completing the job. The data is converted into a custom format and then compressed (loselessly) for storage.

Route is also supported for custom tracker if the tracker provides `data.object.route` object, which should contain a list of `{time, x, z}` data representing the coordinates of the player's location.

The current conversion algorithm (v5) basically follows this procedure:

1. Loop through all coordinates `i = [0, ... , n-1]`. Initialize output `ret = ""`.
2. Calculate the `x` and `z` differences between coordinates `i` and `i+1`.
3. - If the absolute difference for both `x` and `z` are smaller than 26, then convert the differences to `base52` which would be two characters `{rx}{rz}`, append it directly: `ret = ret + {rx}{rz}`.
   - Otherwise, convert the differences to `base52` which would contain more than 2 characters, append it with separators: `ret = ret + ;{rx},{rz};`.
4. Compress the result with `zstandard` (good compression ratio thanks to lots of repetitive characters), then convert it to `base64` printable characters and store in database.

`base52` is essentially mapping an integer from 0 to 51 to a character in `ZYXWVUTSRQPONMLKJIHGFEDCBA0abcdefghijklmnopqrstuvwxyz`. The specific handling differs for the two cases on whether the differences can be stored in only two `base52` characters.

The original algorithm also involves interpolating the data first based on `time` to *smooth out* the route (arguably useless since it's linear interpolation), and also handling idle time. These are not reflected in the above procedure, and you may find more information in `FetchRoute` function in [/src/apis/tracker/custom.py](/src/apis/tracker/custom.py).

The "convert before compress" mechanism achieved surprisingly-good results on saving storage space. No statistics are provided here as the "compression ratio" heavily depends on the original data format and whether the original data was compressed in storage as well. However, it is intuitive and verified that the mechanism saves substantial space compared with storing plain JSON data.

Note that it is technically more space-efficient if we use a binary-based conversion mechanism than the hack-y `base52` mechanism. However, that would overcomplicate the implementation and so it was not pursued.

## Sample Data

This is a sample job that would be accepted by the drivers hub if sent to `/custom/update` endpoint.

You may find more information on the expected data format on [TrackSim Documentation](https://web.archive.org/web/20260312232618/https://docs.tracksim.app/docs/integrations/webhooks).

```jsonc
{
    "object": "event",
    "type": "job.delivered",
    "data": {
        "object": {
            // a dummy 'route' since the original route is lost
            "route": [{"time": 0, "x": 0, "z": 0}],

            // begin actual job data
            "id": 389562,
            "object": "job",
            "driver": {
                "steam_id": "" // only steam id is important
            },
            "start_time": "2023-01-29 23:28:01",
            "stop_time": "2023-01-30 00:20:40",
            "time_spent": 3132,
            "planned_distance": 1181,
            "driven_distance": 1169.59,
            "adblue_used": 19.34,
            "fuel_used": 386.81,
            "is_special": false,
            "is_late": false,
            "market": "freight_market",
            "cargo": {
                "unique_id": "live_cattle",
                "name": "Live Cattle",
                "mass": 14230,
                "damage": 0
            },
            "game": {
                "short_name": "eut2",
                "language": "fr_fr",
                "had_police_enabled": false
            },
            "multiplayer": {
                "type": "truckersmp",
                "server": "ProMods",
                "in_game_id": "513"
            },
            "source_city": {
                "unique_id": "innsbruck",
                "name": "Innsbruck"
            },
            "source_company": {
                "unique_id": "trameri",
                "name": "Trameri"
            },
            "destination_city": {
                "unique_id": "taranto",
                "name": "Taranto"
            },
            "destination_company": {
                "unique_id": "exomar",
                "name": "Exomar"
            },
            "truck": {
                "unique_id": "vehicle.scania.s_2016",
                "name": "S",
                "brand": {
                    "unique_id": "scania",
                    "name": "Scania"
                },
                "odometer": 198280.2656,
                "initial_odometer": 197110.6719,
                "wheel_count": 6,
                "license_plate": "DAVID12567",
                "license_plate_country": {
                    "unique_id": "france",
                    "name": "France"
                },
                "current_damage": {
                    "cabin": 0,
                    "chassis": 0,
                    "engine": 0,
                    "transmission": 0,
                    "wheels": 0.02
                },
                "total_damage": {
                    "cabin": 0.01,
                    "chassis": 0.01,
                    "engine": 0.01,
                    "transmission": 0.01,
                    "wheels": 0.03
                },
                "top_speed": 30.54,
                "average_speed": 22.52
            },
            "trailers": [
                {
                    "name": null,
                    "body_type": "_liveocklile",
                    "chain_type": "single",
                    "wheel_count": 6,
                    "brand": null,
                    "license_plate": "LL 249 ZV",
                    "license_plate_country": {
                        "unique_id": "austria",
                        "name": "Austria"
                    },
                    "current_damage": {
                        "cargo": 0,
                        "chassis": 0,
                        "wheels": 0.02
                    },
                    "total_damage": {
                        "cargo": 0,
                        "chassis": 0,
                        "wheels": 0.02
                    }
                }
            ],
            "events": [
                {
                    "type": "started",
                    "real_time": "2023-01-29 23:28:01",
                    "time": 0,
                    "location": {
                        "x": 3222,
                        "y": 4.9399999999999995,
                        "z": 19566.75
                    },
                    "meta": {}
                },
                {
                    "type": "collision",
                    "real_time": "2023-01-29 23:33:37",
                    "time": 313,
                    "location": {
                        "x": 2964.3,
                        "y": 9.95,
                        "z": 19648.79
                    },
                    "meta": {
                        "wear_engine": "0",
                        "wear_chassis": "0.0132",
                        "wear_transmission": "0",
                        "wear_cabin": "0.0106",
                        "wear_wheels": "0"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:35:44",
                    "time": 440,
                    "location": {
                        "x": 1780.7,
                        "y": 57.72,
                        "z": 21296.41
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0128",
                        "start": "6691",
                        "end": "6710",
                        "from_x": "2144.678307",
                        "from_y": "49.763168",
                        "from_z": "20955.837402",
                        "to_x": "1780.701843",
                        "to_y": "57.718117",
                        "to_z": "21296.412842"
                    }
                },
                {
                    "type": "tollgate",
                    "real_time": "2023-01-29 23:36:19",
                    "time": 475,
                    "location": {
                        "x": 2398.15,
                        "y": 78.54,
                        "z": 21372.29
                    },
                    "meta": {
                        "cost": "45"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:36:24",
                    "time": 480,
                    "location": {
                        "x": 2471.03,
                        "y": 78.53,
                        "z": 21387.15
                    },
                    "meta": {
                        "speed_limit": "8.3333",
                        "max_speed": "11.1128",
                        "start": "6742",
                        "end": "6750",
                        "from_x": "2342.42569",
                        "from_y": "78.532646",
                        "from_z": "21345.486786",
                        "to_x": "2471.026489",
                        "to_y": "78.532814",
                        "to_z": "21387.149689"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:37:56",
                    "time": 572,
                    "location": {
                        "x": 2880.59,
                        "y": 90.65,
                        "z": 22130.67
                    },
                    "meta": {
                        "speed_limit": "13.8889",
                        "max_speed": "27.1706",
                        "start": "6840",
                        "end": "6842",
                        "from_x": "2905.43808",
                        "from_y": "90.647285",
                        "from_z": "22061.928093",
                        "to_x": "2880.593109",
                        "to_y": "90.645859",
                        "to_z": "22130.666626"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:38:47",
                    "time": 623,
                    "location": {
                        "x": 2930.8,
                        "y": 84.74,
                        "z": 23314.22
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "16.6702",
                        "start": "6854",
                        "end": "6893",
                        "from_x": "2968.46283",
                        "from_y": "98.693405",
                        "from_z": "22410.08017",
                        "to_x": "2930.798248",
                        "to_y": "84.744141",
                        "to_z": "23314.215424"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:40:13",
                    "time": 709,
                    "location": {
                        "x": 1914.46,
                        "y": 50.8,
                        "z": 24571.87
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0253",
                        "start": "6936",
                        "end": "6979",
                        "from_x": "2357.462311",
                        "from_y": "63.17815",
                        "from_z": "23735.683624",
                        "to_x": "1914.457611",
                        "to_y": "50.796333",
                        "to_z": "24571.866089"
                    }
                },
                {
                    "type": "repair",
                    "real_time": "2023-01-29 23:40:20",
                    "time": 716,
                    "location": {
                        "x": 1908.13,
                        "y": 49.9,
                        "z": 24637.08
                    },
                    "meta": {}
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:40:59",
                    "time": 755,
                    "location": {
                        "x": 1313.51,
                        "y": 48.84,
                        "z": 25321.11
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0139",
                        "start": "7015",
                        "end": "7025",
                        "from_x": "1563.180708",
                        "from_y": "47.124668",
                        "from_z": "25161.667679",
                        "to_x": "1313.507813",
                        "to_y": "48.836033",
                        "to_z": "25321.108871"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:42:41",
                    "time": 856,
                    "location": {
                        "x": 1076.32,
                        "y": 37.16,
                        "z": 26237.85
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0001",
                        "start": "7112",
                        "end": "7126",
                        "from_x": "888.813324",
                        "from_y": "41.209175",
                        "from_z": "25917.728882",
                        "to_x": "1076.322144",
                        "to_y": "37.163147",
                        "to_z": "26237.852127"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:43:46",
                    "time": 922,
                    "location": {
                        "x": 362.87,
                        "y": 34.39,
                        "z": 27563.57
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0158",
                        "start": "7176",
                        "end": "7192",
                        "from_x": "650.212326",
                        "from_y": "33.679527",
                        "from_z": "27236.780449",
                        "to_x": "362.872528",
                        "to_y": "34.389248",
                        "to_z": "27563.566803"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:47:13",
                    "time": 1129,
                    "location": {
                        "x": -364.75,
                        "y": 36.12,
                        "z": 31629.26
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "23.1028",
                        "start": "7236",
                        "end": "7399",
                        "from_x": "-435.855713",
                        "from_y": "35.110561",
                        "from_z": "27966.454071",
                        "to_x": "-364.753876",
                        "to_y": "36.119392",
                        "to_z": "31629.259674"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:49:19",
                    "time": 1255,
                    "location": {
                        "x": -25.01,
                        "y": 31.59,
                        "z": 34494.47
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "22.282",
                        "start": "7414",
                        "end": "7525",
                        "from_x": "-21.473547",
                        "from_y": "35.577538",
                        "from_z": "31780.824192",
                        "to_x": "-25.013985",
                        "to_y": "31.590181",
                        "to_z": "34494.466797"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-29 23:53:28",
                    "time": 1504,
                    "location": {
                        "x": 4257.52,
                        "y": 39.74,
                        "z": 36076.6
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "23.9066",
                        "start": "7621",
                        "end": "7774",
                        "from_x": "987.407196",
                        "from_y": "38.720406",
                        "from_z": "34672.554291",
                        "to_x": "4257.520798",
                        "to_y": "39.737946",
                        "to_z": "36076.600937"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:04:48",
                    "time": 2183,
                    "location": {
                        "x": 14815.53,
                        "y": 14.83,
                        "z": 48853.81
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.018",
                        "start": "7792",
                        "end": "8453",
                        "from_x": "4621.70066",
                        "from_y": "39.182041",
                        "from_z": "36332.086792",
                        "to_x": "14815.534424",
                        "to_y": "14.829379",
                        "to_z": "48853.814194"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:05:07",
                    "time": 2203,
                    "location": {
                        "x": 15040.39,
                        "y": 14.85,
                        "z": 49060.34
                    },
                    "meta": {
                        "speed_limit": "11.1111",
                        "max_speed": "16.6334",
                        "start": "8467",
                        "end": "8473",
                        "from_x": "14944.723137",
                        "from_y": "14.83558",
                        "from_z": "49042.460419",
                        "to_x": "15040.391953",
                        "to_y": "14.846089",
                        "to_z": "49060.341187"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:10:31",
                    "time": 2527,
                    "location": {
                        "x": 21490.57,
                        "y": 10.97,
                        "z": 53727.4
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "13.9681",
                        "start": "8518",
                        "end": "8797",
                        "from_x": "15983.409348",
                        "from_y": "20.540894",
                        "from_z": "49457.934723",
                        "to_x": "21490.573303",
                        "to_y": "10.973006",
                        "to_z": "53727.398895"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:12:39",
                    "time": 2654,
                    "location": {
                        "x": 23085.75,
                        "y": 9.87,
                        "z": 54843.8
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.087",
                        "start": "8890",
                        "end": "8924",
                        "from_x": "22406.156799",
                        "from_y": "8.636399",
                        "from_z": "54224.55896",
                        "to_x": "23085.750957",
                        "to_y": "9.872106",
                        "to_z": "54843.797775"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:14:47",
                    "time": 2783,
                    "location": {
                        "x": 24981.19,
                        "y": 19.93,
                        "z": 56985.37
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "16.6695",
                        "start": "8962",
                        "end": "9053",
                        "from_x": "23915.601135",
                        "from_y": "11.460634",
                        "from_z": "54998.763779",
                        "to_x": "24981.185059",
                        "to_y": "19.931763",
                        "to_z": "56985.366837"
                    }
                },
                {
                    "type": "tollgate",
                    "real_time": "2023-01-30 00:14:48",
                    "time": 2784,
                    "location": {
                        "x": 24992.44,
                        "y": 19.93,
                        "z": 56995.1
                    },
                    "meta": {
                        "cost": "221"
                    }
                },
                {
                    "type": "speeding",
                    "real_time": "2023-01-30 00:17:19",
                    "time": 2934,
                    "location": {
                        "x": 27095.54,
                        "y": 28.94,
                        "z": 57120.32
                    },
                    "meta": {
                        "speed_limit": "22.2222",
                        "max_speed": "25.0034",
                        "start": "9182",
                        "end": "9204",
                        "from_x": "26494.280792",
                        "from_y": "28.94441",
                        "from_z": "57171.177032",
                        "to_x": "27095.539154",
                        "to_y": "28.935619",
                        "to_z": "57120.315247"
                    }
                },
                {
                    "type": "delivered",
                    "real_time": "2023-01-30 00:20:40",
                    "time": 3132,
                    "location": {
                        "x": 26503.28,
                        "y": 24.94,
                        "z": 56897.19
                    },
                    "meta": {
                        "revenue": "64737",
                        "earned_xp": "1734",
                        "cargo_damage": "0",
                        "distance": "1170",
                        "delivery_time": "316",
                        "auto_park": "0",
                        "auto_load": "1"
                    }
                }
            ],
            "mods": []
        }
    }
}
```
