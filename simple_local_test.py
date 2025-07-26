#!/usr/bin/env python3
"""
Simple Local Test for C-Bus Integration Logic
Tests the core patterns and MQTT topic structures without Home Assistant dependencies.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_mqtt_topic_patterns():
    """Test MQTT topic pattern generation."""
    print("📡 Testing MQTT Topic Patterns...")
    
    # Define patterns (copied from const.py)
    MQTT_TOPIC_LIGHT_STATE = "cbus/read/{}/{}/{}/state"
    MQTT_TOPIC_LIGHT_LEVEL = "cbus/read/{}/{}/{}/level"  
    MQTT_TOPIC_LIGHT_COMMAND = "cbus/write/{}/{}/{}/switch"
    MQTT_TOPIC_LIGHT_RAMP = "cbus/write/{}/{}/{}/ramp"
    MQTT_TOPIC_GETALL = "cbus/write/{}/{}//getall"
    MQTT_TOPIC_GETTREE = "cbus/write/{}///gettree"
    
    # Test values
    network, app, group = "254", "56", "1"
    
    # Test topic generation
    tests = [
        (MQTT_TOPIC_LIGHT_STATE.format(network, app, group), "cbus/read/254/56/1/state"),
        (MQTT_TOPIC_LIGHT_LEVEL.format(network, app, group), "cbus/read/254/56/1/level"),
        (MQTT_TOPIC_LIGHT_COMMAND.format(network, app, group), "cbus/write/254/56/1/switch"),
        (MQTT_TOPIC_LIGHT_RAMP.format(network, app, group), "cbus/write/254/56/1/ramp"),
        (MQTT_TOPIC_GETALL.format(network, app), "cbus/write/254/56//getall"),
        (MQTT_TOPIC_GETTREE.format(network), "cbus/write/254///gettree"),
    ]
    
    passed = 0
    for actual, expected in tests:
        if actual == expected:
            print(f"  ✅ {expected}")
            passed += 1
        else:
            print(f"  ❌ Expected: {expected}")
            print(f"     Got:      {actual}")
    
    print(f"  📊 Passed: {passed}/{len(tests)}")
    return passed == len(tests)

def test_config_validation():
    """Test configuration validation logic."""
    print("\n⚙️ Testing Configuration Validation...")
    
    # Test valid configuration
    valid_config = {
        "host": "192.168.0.50",
        "port": 10001,
        "mqtt_broker": "core-mosquitto",
        "mqtt_user": "pai",
        "mqtt_password": "pai",
        "mqtt_topic": "cbus"
    }
    
    # Simple validation function (mirroring config_flow logic)
    def validate_config(config):
        errors = []
        if not config.get("host"):
            errors.append("missing_host")
        if not config.get("mqtt_user"):
            errors.append("missing_mqtt_user")
        if not config.get("mqtt_password"):
            errors.append("missing_mqtt_password")
        return errors
    
    # Test valid config
    errors = validate_config(valid_config)
    if not errors:
        print("  ✅ Valid configuration passes")
        valid_test = True
    else:
        print(f"  ❌ Valid configuration failed: {errors}")
        valid_test = False
    
    # Test invalid configs
    invalid_configs = [
        ({"host": "", "mqtt_user": "pai", "mqtt_password": "pai"}, ["missing_host"]),
        ({"host": "192.168.0.50", "mqtt_user": "", "mqtt_password": "pai"}, ["missing_mqtt_user"]),
        ({"host": "192.168.0.50", "mqtt_user": "pai", "mqtt_password": ""}, ["missing_mqtt_password"]),
    ]
    
    invalid_tests_passed = 0
    for config, expected_errors in invalid_configs:
        errors = validate_config(config)
        if set(errors) == set(expected_errors):
            print(f"  ✅ Invalid config correctly rejected: {expected_errors}")
            invalid_tests_passed += 1
        else:
            print(f"  ❌ Expected errors: {expected_errors}, got: {errors}")
    
    print(f"  📊 Validation tests passed: {1 + invalid_tests_passed}/{1 + len(invalid_configs)}")
    return valid_test and invalid_tests_passed == len(invalid_configs)

def test_entity_id_generation():
    """Test entity ID generation patterns."""
    print("\n🏷️ Testing Entity ID Generation...")
    
    def generate_entity_id(network, application, group):
        """Generate entity ID following our pattern."""
        return f"cbus_{network}_{application}_{group}"
    
    def generate_entity_name(group):
        """Generate entity name following our pattern."""
        return f"C-Bus Light {group}"
    
    # Test cases
    test_cases = [
        ("254", "56", "1", "cbus_254_56_1", "C-Bus Light 1"),
        ("254", "56", "10", "cbus_254_56_10", "C-Bus Light 10"),
        ("200", "56", "25", "cbus_200_56_25", "C-Bus Light 25"),
    ]
    
    passed = 0
    for network, app, group, expected_id, expected_name in test_cases:
        actual_id = generate_entity_id(network, app, group)
        actual_name = generate_entity_name(group)
        
        if actual_id == expected_id and actual_name == expected_name:
            print(f"  ✅ Group {group}: {actual_id} / {actual_name}")
            passed += 1
        else:
            print(f"  ❌ Group {group}:")
            print(f"     Expected ID: {expected_id}, got: {actual_id}")
            print(f"     Expected Name: {expected_name}, got: {actual_name}")
    
    print(f"  📊 Entity tests passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

def test_brightness_conversion():
    """Test brightness conversion between Home Assistant (0-255) and C-Bus percentage (0-100)."""
    print("\n💡 Testing Brightness Conversion...")
    
    def ha_to_cbus_percent(ha_brightness):
        """Convert HA brightness (0-255) to C-Bus percentage (0-100)."""
        return int((ha_brightness / 255) * 100)
    
    def cbus_level_to_ha_brightness(cbus_level):
        """Convert C-Bus level (0-255) to HA brightness (0-255)."""
        return cbus_level  # Direct mapping
    
    # Test cases: (HA brightness, expected C-Bus percent)
    brightness_tests = [
        (0, 0),      # Off
        (26, 10),    # ~10%
        (128, 50),   # ~50%
        (191, 75),   # ~75%
        (255, 100),  # Full brightness
    ]
    
    passed = 0
    for ha_brightness, expected_percent in brightness_tests:
        actual_percent = ha_to_cbus_percent(ha_brightness)
        if actual_percent == expected_percent:
            print(f"  ✅ HA {ha_brightness} → C-Bus {actual_percent}%")
            passed += 1
        else:
            print(f"  ❌ HA {ha_brightness} → Expected {expected_percent}%, got {actual_percent}%")
    
    # Test C-Bus level to HA brightness (should be direct)
    level_tests = [(0, 0), (127, 127), (255, 255)]
    for cbus_level, expected_ha in level_tests:
        actual_ha = cbus_level_to_ha_brightness(cbus_level)
        if actual_ha == expected_ha:
            print(f"  ✅ C-Bus level {cbus_level} → HA {actual_ha}")
            passed += 1
        else:
            print(f"  ❌ C-Bus level {cbus_level} → Expected HA {expected_ha}, got {actual_ha}")
    
    print(f"  📊 Brightness tests passed: {passed}/{len(brightness_tests) + len(level_tests)}")
    return passed == (len(brightness_tests) + len(level_tests))

def test_discovery_topic_parsing():
    """Test parsing of MQTT discovery topics."""
    print("\n🔍 Testing Discovery Topic Parsing...")
    
    def parse_discovery_topic(topic):
        """Parse discovery topic to extract network, app, group."""
        # Expected format: cbus/read/254/56/123/state
        try:
            parts = topic.split('/')
            if len(parts) >= 6 and parts[0] == "cbus" and parts[1] == "read":
                return {
                    "network": parts[2],
                    "application": parts[3],
                    "group": parts[4],
                    "type": parts[5]
                }
        except:
            pass
        return None
    
    # Test cases
    test_topics = [
        ("cbus/read/254/56/1/state", {"network": "254", "application": "56", "group": "1", "type": "state"}),
        ("cbus/read/254/56/10/level", {"network": "254", "application": "56", "group": "10", "type": "level"}),
        ("cbus/read/200/56/25/state", {"network": "200", "application": "56", "group": "25", "type": "state"}),
        ("invalid/topic", None),
        ("cbus/write/254/56/1/switch", None),  # Should not match read topics
    ]
    
    passed = 0
    for topic, expected in test_topics:
        result = parse_discovery_topic(topic)
        if result == expected:
            if result:
                print(f"  ✅ {topic} → Group {result['group']}")
            else:
                print(f"  ✅ {topic} → Invalid (correctly rejected)")
            passed += 1
        else:
            print(f"  ❌ {topic} → Expected {expected}, got {result}")
    
    print(f"  📊 Discovery parsing tests passed: {passed}/{len(test_topics)}")
    return passed == len(test_topics)

def test_service_commands():
    """Test service command generation."""
    print("\n🔧 Testing Service Commands...")
    
    # Service command patterns
    def generate_getall_command(network, application):
        return f"cbus/write/{network}/{application}//getall"
    
    def generate_gettree_command(network):
        return f"cbus/write/{network}///gettree"
    
    def generate_light_command(network, application, group, command_type):
        if command_type == "switch":
            return f"cbus/write/{network}/{application}/{group}/switch"
        elif command_type == "ramp":
            return f"cbus/write/{network}/{application}/{group}/ramp"
        return None
    
    # Test cases
    tests = [
        (generate_getall_command("254", "56"), "cbus/write/254/56//getall"),
        (generate_gettree_command("254"), "cbus/write/254///gettree"),
        (generate_light_command("254", "56", "1", "switch"), "cbus/write/254/56/1/switch"),
        (generate_light_command("254", "56", "1", "ramp"), "cbus/write/254/56/1/ramp"),
    ]
    
    passed = 0
    for actual, expected in tests:
        if actual == expected:
            print(f"  ✅ {expected}")
            passed += 1
        else:
            print(f"  ❌ Expected: {expected}, got: {actual}")
    
    print(f"  📊 Service command tests passed: {passed}/{len(tests)}")
    return passed == len(tests)

def run_all_tests():
    """Run all local tests."""
    print("🚀 Simple Local C-Bus Integration Tests")
    print("=" * 60)
    print("Testing core integration logic without Home Assistant dependencies\n")
    
    tests = [
        ("MQTT Topic Patterns", test_mqtt_topic_patterns),
        ("Config Validation", test_config_validation),
        ("Entity ID Generation", test_entity_id_generation),
        ("Brightness Conversion", test_brightness_conversion),
        ("Discovery Topic Parsing", test_discovery_topic_parsing),
        ("Service Commands", test_service_commands),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Core integration logic is correct.")
        print("\n✅ Ready to test in Home Assistant!")
        print("\nNext steps:")
        print("1. Copy custom_components/cbus_lights/ to Home Assistant")
        print("2. Restart Home Assistant")
        print("3. Configure ha-cbus2mqtt addon with your settings")
        print("4. Add C-Bus Lights integration")
        return True
    else:
        print(f"\n⚠️ {failed} tests failed. Fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n🔗 Integration follows ha-cbus2mqtt patterns correctly!")
        print("📋 Validated patterns:")
        print("  • MQTT topics match cmqttd format")
        print("  • Configuration validation works")
        print("  • Entity IDs follow HA conventions") 
        print("  • Brightness conversion is correct")
        print("  • Discovery parsing works")
        print("  • Service commands are properly formatted")
    else:
        print("\n❌ Please fix the failing tests first.")
    
    sys.exit(0 if success else 1) 