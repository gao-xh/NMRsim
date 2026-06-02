# Tests

Test scripts for verifying functionality.

## Available Tests

### test_bridge_variables.py
Tests MATLAB Spinach bridge variable handling.

Usage:
```python
python tests/test_bridge_variables.py
```

### test_splash.py
Tests the splash screen display (shows splash screen only, no initialization).

Usage:
```python
python tests/test_splash.py
```

## Running Tests

Make sure you are in the matlab312 environment:
```bash
conda activate matlab312
cd tests
python test_name.py
```

## Test Coverage

- MATLAB bridge functionality
- UI component display
- Data validation

For comprehensive testing, ensure MATLAB and all dependencies are properly installed.
