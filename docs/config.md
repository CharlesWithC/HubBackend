# Configuration

See [docs/config.jsonc](./config.jsonc) for a sample configuration with detailed documentations.

## Bonus

`config.rank_types[].details[].bonus` format

- `min_distance`/`max_distance`: int
- `probability`: float = 0~1
- `type`: str = `fixed_value`/`fixed_percentage`/`random_value`/`random_percentage`
- `val`: int/float when `type` is `fixed_*`
- `min`/`max`: int/float when `type` is `random_*`

`config.rank_types[].details[].daily_bonus` format

- `base`: int
- `type`: str = `fixed`/`streak`
- `streak_type`: str = `fixed`/`percentage`/`algo` when `type` is `streak`
- `streak_value`: int when `streak_type` is `fixed` / float when `streak_type` is `percentage`/`algo` when `type` is `streak`
- `algo_offset`: positive float when `streak_type` is `algo`, controls the initial growth rate of the result

## Discord Message Variables

Member accepted: `{mention}, {name}, {userid}, {uid}, {avatar}, {staff_mention}, {staff_name}, {staff_userid}, {staff_uid}, {staff_avatar}`  
Member resigned: `{mention}, {name}, {userid}, {uid}, {avatar}`  
Member dismissed: `{mention}, {name}, {userid}, {uid}, {avatar}, {staff_mention}, {staff_name}, {staff_userid}, {staff_uid}, {staff_avatar}`  
Update roles: `{mention}, {name}, {userid}, {uid}, {avatar}, {staff_mention}, {staff_name}, {staff_userid}, {staff_uid}, {staff_avatar}`  
Driver ranked up: `{mention}, {name}, {userid}, {rank}, {uid}, {avatar}`  
New announcement: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {content}, {type}`  
New challenge: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {description}, {start_timestamp}, {end_timestamp}, {delivery_count}, {required_roles}, {required_distance}, {reward_points}`  
Challenge completed / point updated: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {earned_points}`  
New downloadable item: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {description}, {link}`  
New event: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {description}, {link}, {departure}, {destination}, {distance}, {meetup_timestamp}, {departure_timestamp}`  
Upcoming event: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {description}, {link}, {departure}, {destination}, {distance}, {meetup_timestamp}, {departure_timestamp}`  
New poll: `{mention}, {name}, {userid}, {uid}, {avatar}, {id}, {title}, {description}`  
