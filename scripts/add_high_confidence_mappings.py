#!/usr/bin/env python3
"""Add high confidence mappings."""

import json
from pathlib import Path

# High confidence mappings (manually reviewed)
NEW_MAPPINGS = [
    # High confidence from script
    {"InputDtmi": "dtmi:com:willowinc:airport:AirportAudioVisualEquipment;1", "OutputDtmi": "dtmi:mapped:core:Audio_Visual_Equipment;1"},
    {"InputDtmi": "dtmi:com:willowinc:NeutralDeckInletDamper;1", "OutputDtmi": "dtmi:mapped:core:Neutral_Deck_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:OutsideAirDamper;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Outside_Damper;1"},  # Corrected
    {"InputDtmi": "dtmi:com:willowinc:PitLoadingDockLeveler;1", "OutputDtmi": "dtmi:mapped:core:Loading_Dock_Leveler;1"},
    {"InputDtmi": "dtmi:com:willowinc:RailLoadingDockLeveler;1", "OutputDtmi": "dtmi:mapped:core:Loading_Dock_Leveler;1"},

    # Good medium confidence (reviewed)
    {"InputDtmi": "dtmi:com:willowinc:ColdDeckInletDamper;1", "OutputDtmi": "dtmi:mapped:core:Cold_Deck_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:HotDeckInletDamper;1", "OutputDtmi": "dtmi:mapped:core:Hot_Deck_Damper;1"},
    {"InputDtmi": "dtmi:com:willowinc:airport:AircraftGroundPowerUnit;1", "OutputDtmi": "dtmi:mapped:core:Ground_Power_Unit;1"},
    {"InputDtmi": "dtmi:com:willowinc:AirCooledHeatRecoveryChiller;1", "OutputDtmi": "dtmi:mapped:core:Heat_Recovery_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:WaterCooledHeatRecoveryChiller;1", "OutputDtmi": "dtmi:mapped:core:Heat_Recovery_Chiller;1"},
    {"InputDtmi": "dtmi:com:willowinc:BenchtopFumeHood;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fume_Hood;1"},
    {"InputDtmi": "dtmi:com:willowinc:WalkInFumeHood;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fume_Hood;1"},
    {"InputDtmi": "dtmi:com:willowinc:SnorkelExhaustFumeHood;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fume_Hood;1"},
    {"InputDtmi": "dtmi:com:willowinc:BollardLuminaire;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Luminaire;1"},
    {"InputDtmi": "dtmi:com:willowinc:IndoorLuminaire;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Luminaire;1"},
    {"InputDtmi": "dtmi:com:willowinc:OutdoorLuminaire;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Luminaire;1"},
    {"InputDtmi": "dtmi:com:willowinc:LightPole;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Luminaire;1"},

    # Valves
    {"InputDtmi": "dtmi:com:willowinc:HVACValve;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:HVAC_Valve;1"},
    {"InputDtmi": "dtmi:com:willowinc:PlumbingValve;1", "OutputDtmi": "dtmi:mapped:core:Plumbing_Valve;1"},

    # Pumps
    {"InputDtmi": "dtmi:com:willowinc:HVACPump;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:HVAC_Pump;1"},
    {"InputDtmi": "dtmi:com:willowinc:PlumbingPump;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Plumbing_Pump;1"},
    {"InputDtmi": "dtmi:com:willowinc:HydronicPump;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Water_Pump;1"},

    # Filters
    {"InputDtmi": "dtmi:com:willowinc:AirFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Filter;1"},
    {"InputDtmi": "dtmi:com:willowinc:OutsideAirFilter;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Intake_Air_Filter;1"},

    # Coils (children of already mapped coils)
    {"InputDtmi": "dtmi:com:willowinc:DirectExpansionCoolingCoil;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Direct_Expansion_Cooling_Coil;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledWaterCoolingCoil;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chilled_Water_Coil;1"},

    # Boilers
    {"InputDtmi": "dtmi:com:willowinc:CondensingBoiler;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Condensing_Natural_Gas_Boiler;1"},
    {"InputDtmi": "dtmi:com:willowinc:NonCondensingBoiler;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Noncondensing_Natural_Gas_Boiler;1"},

    # Terminal Units
    {"InputDtmi": "dtmi:com:willowinc:TerminalUnit;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Terminal_Unit;1"},
    {"InputDtmi": "dtmi:com:willowinc:VAVBox;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Variable_Air_Volume_Box;1"},
    {"InputDtmi": "dtmi:com:willowinc:DualDuctVAVBox;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Dual_Duct_Variable_Air_Volume_Box;1"},
    {"InputDtmi": "dtmi:com:willowinc:VAVBoxReheat;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Variable_Air_Volume_Box_With_Reheat;1"},
    {"InputDtmi": "dtmi:com:willowinc:FanPoweredBox;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fan_Powered_VAV;1"},
    {"InputDtmi": "dtmi:com:willowinc:FanPoweredBoxReheat;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fan_Powered_VAV_With_Reheat;1"},
    {"InputDtmi": "dtmi:com:willowinc:CAVBox;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Constant_Air_Volume_Box;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledBeam;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chilled_Beam;1"},
    {"InputDtmi": "dtmi:com:willowinc:ActiveChilledBeam;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Active_Chilled_Beam;1"},
    {"InputDtmi": "dtmi:com:willowinc:PassiveChilledBeam;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Passive_Chilled_Beam;1"},

    # Heat Exchangers
    {"InputDtmi": "dtmi:com:willowinc:PlateHeatExchanger;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Heat_Exchanger;1"},
    {"InputDtmi": "dtmi:com:willowinc:ShellAndTubeHeatExchanger;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Heat_Exchanger;1"},

    # Cooling Towers
    {"InputDtmi": "dtmi:com:willowinc:DryCooler;1", "OutputDtmi": "dtmi:mapped:core:Dry_Cooler;1"},

    # Radiant heating
    {"InputDtmi": "dtmi:com:willowinc:RadiantHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Radiator;1"},
    {"InputDtmi": "dtmi:com:willowinc:HydronicRadiantHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Hot_Water_Radiator;1"},
    {"InputDtmi": "dtmi:com:willowinc:ElectricRadiantHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Electric_Radiator;1"},
    {"InputDtmi": "dtmi:com:willowinc:HydronicBaseboardHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Hot_Water_Baseboard_Radiator;1"},

    # Unit Heaters
    {"InputDtmi": "dtmi:com:willowinc:UnitHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Unit_Heater;1"},
    {"InputDtmi": "dtmi:com:willowinc:HotWaterUnitHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Unit_Heater;1"},
    {"InputDtmi": "dtmi:com:willowinc:SteamUnitHeater;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Unit_Heater;1"},

    # Spaces
    {"InputDtmi": "dtmi:com:willowinc:Room;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Room;1"},
    {"InputDtmi": "dtmi:com:willowinc:Zone;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Zone;1"},
    {"InputDtmi": "dtmi:com:willowinc:HVACZone;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:HVAC_Zone;1"},
    {"InputDtmi": "dtmi:com:willowinc:LightingZone;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Lighting_Zone;1"},
    {"InputDtmi": "dtmi:com:willowinc:OccupancyZone;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Occupancy_Zone;1"},
    {"InputDtmi": "dtmi:com:willowinc:OutdoorArea;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Outdoor_Area;1"},
    {"InputDtmi": "dtmi:com:willowinc:Land;1", "OutputDtmi": "dtmi:mapped:core:Site;1"},
    {"InputDtmi": "dtmi:com:willowinc:SubBuilding;1", "OutputDtmi": "dtmi:mapped:core:SubBuilding;1"},

    # Collections
    {"InputDtmi": "dtmi:com:willowinc:AssetCollection;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Collection;1"},
    {"InputDtmi": "dtmi:com:willowinc:SpaceCollection;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Collection;1"},
    {"InputDtmi": "dtmi:com:willowinc:DocumentCollection;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Collection;1"},
    {"InputDtmi": "dtmi:com:willowinc:EquipmentCollection;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Collection;1"},
    {"InputDtmi": "dtmi:com:willowinc:EquipmentGroup;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Collection;1"},

    # Systems
    {"InputDtmi": "dtmi:com:willowinc:HVACSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:HVAC_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:PlumbingSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Plumbing_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:LightingSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Lighting_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:SecuritySystem;1", "OutputDtmi": "dtmi:mapped:core:Security_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:FireProtectionSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fire_Safety_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:FireAlarmSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Fire_Safety_System;1"},
    {"InputDtmi": "dtmi:com:willowinc:SprinklerSystem;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Sprinkler_System;1"},

    # Chiller groups/plants
    {"InputDtmi": "dtmi:com:willowinc:ChillerGroup;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chiller_Group;1"},
    {"InputDtmi": "dtmi:com:willowinc:CoolingTowerGroup;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Cooling_Tower_Group;1"},
    {"InputDtmi": "dtmi:com:willowinc:CoolingPlant;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chiller_Plant;1"},
    {"InputDtmi": "dtmi:com:willowinc:ChilledWaterPlant;1", "OutputDtmi": "dtmi:org:brickschema:schema:Brick:Chiller_Plant;1"},
]


def main():
    filepath = Path(__file__).parent.parent / 'data' / 'Willow2Mapped.json'

    with open(filepath, 'r') as f:
        data = json.load(f)

    existing = {m['InputDtmi'] for m in data['InterfaceRemaps']}

    added = 0
    for mapping in NEW_MAPPINGS:
        if mapping['InputDtmi'] not in existing:
            data['InterfaceRemaps'].append(mapping)
            added += 1
            print(f"Added: {mapping['InputDtmi'].split(':')[-1].replace(';1', '')}")
        else:
            print(f"Skipped (exists): {mapping['InputDtmi'].split(':')[-1].replace(';1', '')}")

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nAdded {added} new mappings")


if __name__ == '__main__':
    main()
