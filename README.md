# Home Assistant – Dunedin City Council (kerbside collection)

A HACS custom integration that tells Home Assistant when your Dunedin kerbside bins are collected, including which bins go out each week and public-holiday shifts. Modelled on [osotechie/ha_aucklandcouncil](https://github.com/osotechie/ha_aucklandcouncil).

Not affiliated with Dunedin City Council. Data comes from the council's public map service that powers the [Kerbside collection days](https://www.dunedin.govt.nz/do-it-online/search/collection-days) lookup.

## Install

**HACS:** HACS → ⋮ → Custom repositories → add this repo as an *Integration* → download → restart Home Assistant.

**Manual:** copy `custom_components/dunedin_council/` into your `config/custom_components/` folder and restart.

## Set up

Settings → Devices & Services → Add Integration → **Dunedin City Council**. Type your street address (e.g. `118 High Street`), then pick your property from the list. Multi-unit buildings usually have one entry per unit; the council recommends trying the address *without* the unit number if you don't see yours.

If you live in the **Tertiary (student) area**, tick that box: all bins are collected weekly there. You can change it later under the integration's *Configure* button.

## Entities

| Entity | State | Notes |
|---|---|---|
| Food scraps & garden (green) | next collection date | weekly |
| Rubbish (red) | next collection date | fortnightly, same week as glass |
| Glass (blue) | next collection date | fortnightly |
| Mixed recycling (yellow) | next collection date | fortnightly, alternate week |
| Next collection | e.g. `Food scraps & garden, Mixed recycling` | attributes: `date`, `days_until`, `bins` |
| Collection day | e.g. `Wednesday` | attributes include the raw council week code for debugging |

Date sensors also carry a `days_until` attribute, refreshed at midnight.

## Example: reminder the evening before

```yaml
alias: Bin night reminder
triggers:
  - trigger: time
    at: "19:30:00"
conditions:
  - condition: template
    value_template: >
      {{ state_attr('sensor.YOUR_ADDRESS_next_collection', 'days_until') == 1 }}
actions:
  - action: notify.notify
    data:
      title: Bins out tonight
      message: "{{ states('sensor.YOUR_ADDRESS_next_collection') }}"
```

Replace the entity ID with yours (Settings → Entities).

## How the schedule is worked out

The council's map layer reports your collection weekday and whether the *current* week is a "blue" or "yellow" week. On each refresh (every 6 hours) the integration anchors on that value and alternates week by week from there. Rubbish and glass go out in the blue week, mixed recycling in the yellow week, food/garden every week. No collection on Good Friday, Christmas Day or New Year's Day when they fall on a weekday: those collections move to the following Saturday.

## Troubleshooting

**Fortnightly bins show the wrong week.** Look at what's actually out on your street this week and compare to the sensors. If they're backwards, open the integration → *Configure* → tick **Swap blue/yellow weeks**.

**Fortnightly sensors show Unknown.** The council's week code wasn't recognised. Check the *Collection day* sensor's `council_current_week_code` attribute and the Home Assistant log, then open an issue with the value.

**Check the raw data yourself** by opening this in a browser (change the address):

```
https://apps.dunedin.govt.nz/arcgis/rest/services/Public/Refuse_Collection_Property/MapServer/1/query?where=UPPER(fmtaddress)%20LIKE%20%27%25118%20HIGH%20STREET%25%27&outFields=*&returnGeometry=false&f=json
```

Look at `collectionDay`, `numberDay` (1 = Monday) and `CurrentWeek`.

## Development

```
pip install pytest aiohttp
pytest tests/
```

Tests cover the schedule logic (alternation, holiday shifts, tertiary area) and the API client's query building. They don't need Home Assistant.

## Licence

MIT – add a `LICENSE` file when you publish.
