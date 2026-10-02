#!/usr/bin/env python3
"""Add new mappings to Willow2Mapped.json."""

import json
from pathlib import Path

# Exact matches to add
NEW_MAPPINGS = [
    {"InputDtmi": "dtmi:com:willowinc:AbsorptionChiller;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Absorption_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:AirCooledHeatPumpChiller;1", "OutputDtmi": "dtmi:mapped:core:Air_Cooled_Heat_Pump_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:BoilerGroup;1", "OutputDtmi": "dtmi:mapped:core:Boiler_Group;1"},
    {"InputDtmi": "dtmi:com:willowinc:BoosterFan;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Booster_Fan;1"},
    {"InputDtmi": "dtmi:com:willowinc:BypassDamper;1", "OutputDtmi": "dtmi:mapped:core:Bypass_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:BypassValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Bypass_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledWaterMeter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chilled_Water_Meter;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledWaterPump;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chilled_Water_Pump;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledWaterValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chilled_Water_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:CondenserWaterPump;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Condenser_Water_Pump;1"},
    {"InputDtmi": "dtmi:com:willowinc:CondenserWaterValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Condenser_Water_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:Dehumidifier;1", "OutputDtmi": "dtmi:mapped:core:Dehumidifier;1"},
    {"InputDtmi": "dtmi:com:willowinc:EconomizerDamper;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Economizer_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:ElectronicExpansionValve;1", "OutputDtmi": "dtmi:mapped:core:Electronic_Expansion_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:ElevatorPressurizationFan;1", "OutputDtmi": "dtmi:mapped:core:Elevator_Pressurization_Fan;1"},
    {"InputDtmi": "dtmi:com:willowinc:ExhaustDamper;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Exhaust_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:FaceAndBypassDamper;1", "OutputDtmi": "dtmi:mapped:core:Face_And_Bypass_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:Fan;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fan;1"},
    {"InputDtmi": "dtmi:com:willowinc:FinalFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Final_Filter;1"},
    {"InputDtmi": "dtmi:com:willowinc:FloorBuffer;1", "OutputDtmi": "dtmi:mapped:core:Floor_Buffer;1"},
    {"InputDtmi": "dtmi:com:willowinc:FumeHood;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fume_Hood;1"},
    {"InputDtmi": "dtmi:com:willowinc:HVACHeatExchangerGroup;1", "OutputDtmi": "dtmi:mapped:core:Heat_Exchanger_Group;1"},
    {"InputDtmi": "dtmi:com:willowinc:HeatDetector;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Heat_Detector;1"},
    {"InputDtmi": "dtmi:com:willowinc:HeatPumpChiller;1", "OutputDtmi": "dtmi:mapped:core:Heat_Pump_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:HeatRecoveryChiller;1", "OutputDtmi": "dtmi:mapped:core:Heat_Recovery_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:HotWaterMeter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Hot_Water_Meter;1"},
    {"InputDtmi": "dtmi:com:willowinc:Inverter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Inverter;1"},
    {"InputDtmi": "dtmi:com:willowinc:IsolationValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Isolation_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:MezzanineLevel;1", "OutputDtmi": "dtmi:org:w3id:rec:MezzanineLevel;1"},
    {"InputDtmi": "dtmi:com:willowinc:MinOutsideAirDamper;1", "OutputDtmi": "dtmi:mapped:core:Min_Outside_Air_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:MixedAirFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Mixed_Air_Filter;1"},
    {"InputDtmi": "dtmi:com:willowinc:MixedDamper;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Mixed_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:PackagedAirConditioner;1", "OutputDtmi": "dtmi:mapped:core:Packaged_Air_Conditioner;1"},
    {"InputDtmi": "dtmi:com:willowinc:PreFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Pre_Filter;1"},
    {"InputDtmi": "dtmi:com:willowinc:PreheatHotWaterValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Preheat_Hot_Water_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:PressurizationFan;1", "OutputDtmi": "dtmi:mapped:core:Pressurization_Fan;1"},
    {"InputDtmi": "dtmi:com:willowinc:RefrigerantMeteringDevice;1", "OutputDtmi": "dtmi:mapped:core:Refrigerant_Metering_Device;1"},
    {"InputDtmi": "dtmi:com:willowinc:RefrigerantValve;1", "OutputDtmi": "dtmi:mapped:core:Refrigerant_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:ReliefFan;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Relief_Fan;1"},
    {"InputDtmi": "dtmi:com:willowinc:ReturnAirFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Return_Air_Filter;1"},
    {"InputDtmi": "dtmi:com:willowinc:ReturnDamper;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Return_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:ReversingValve;1", "OutputDtmi": "dtmi:mapped:core:Reversing_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:SteamValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Steam_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:ThermalExpansionValve;1", "OutputDtmi": "dtmi:mapped:core:Thermal_Expansion_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:Turnstile;1", "OutputDtmi": "dtmi:mapped:core:Turnstile;1"},
    {"InputDtmi": "dtmi:com:willowinc:Vehicle;1", "OutputDtmi": "dtmi:mapped:core:Vehicle;1"},
    {"InputDtmi": "dtmi:com:willowinc:WaterCooledHeatPumpChiller;1", "OutputDtmi": "dtmi:mapped:core:Water_Cooled_Heat_Pump_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:Workspace;1", "OutputDtmi": "dtmi:org:w3id:rec:Workspace;1"},
    {"InputDtmi": "dtmi:com:willowinc:ZoneDamper;1", "OutputDtmi": "dtmi:mapped:core:Zone_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:airport:AircraftStand;1", "OutputDtmi": "dtmi:mapped:core:Aircraft_Stand;1"},
    {"InputDtmi": "dtmi:com:willowinc:airport:AirportGate;1", "OutputDtmi": "dtmi:mapped:core:Gate;1"},
    {"InputDtmi": "dtmi:com:willowinc:airport:FlightInformationDisplay;1", "OutputDtmi": "dtmi:mapped:core:Display;1"},
    {"InputDtmi": "dtmi:com:willowinc:airport:PassengerBoardingBridge;1", "OutputDtmi": "dtmi:mapped:core:Passenger_Boarding_Bridge;1"},
]


def main():
    filepath = Path(__file__).parent.parent / 'data' / 'Willow2Mapped.json'

    # Load existing mappings
    with open(filepath, 'r') as f:
        data = json.load(f)

    existing = {m['InputDtmi'] for m in data['InterfaceRemaps']}

    # Add new mappings (skip if already exists)
    added = 0
    for mapping in NEW_MAPPINGS:
        if mapping['InputDtmi'] not in existing:
            data['InterfaceRemaps'].append(mapping)
            added += 1
            print(f"Added: {mapping['InputDtmi']}")
        else:
            print(f"Skipped (exists): {mapping['InputDtmi']}")

    # Write back
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nAdded {added} new mappings")


if __name__ == '__main__':
    main()
