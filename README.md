# Avg Demand Prediction

This Home Assistant integration tries to predict the average demand at the end of the quarter-hour, based on the current demand and the demand of the previous quarter-hour. The prediction is based on data from the current average demand.

## Installation
1. Copy the contents of this repository to `<config_dir>/custom_components/avg_demand_prediction/`.
2. Restart Home Assistant.

## Configuration
Add the following to your `configuration.yaml` file:

```yaml
sensor:
  - platform: avg_demand_prediction
    current_avg_demand_sensor: sensor.current_avg_demand
    name: Avg Demand Prediction
```

### Configuration Variables
**current_avg_demand_sensor:**\
  *(string)*\
  The sensor that contains the current average demand.

**power_consumed_sensor:**\
  *(string)(Optional)*\
  The sensor that contains the current power consumption (kW). This sensor is currently not used.

**name:**\
    *(string)(Optional)*\
    The name of the sensor.




