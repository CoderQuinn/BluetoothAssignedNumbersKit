# BluetoothAssignedNumbersKit

Private Swift Package that converts the authoritative Bluetooth SIG Assigned Numbers repository into a versioned, offline JSON catalog.

The bundled snapshot covers:

- Bluetooth SIG Company Identifiers
- GATT Service UUIDs
- GATT Characteristic UUIDs
- GATT Descriptor UUIDs
- GAP Appearance category and subcategory values

Runtime lookup is fully offline. Updating data is a separate, explicit build-time operation.

## Usage

```swift
import BluetoothAssignedNumbersKit

let catalog = try BluetoothAssignedNumbersCatalog.bundled()
let vendor = catalog.companyName(forHex: "0x004C")
let service = catalog.name(for: "180D", kind: .service)
let appearance = catalog.appearance(for: 0x0081)
```

## Update contract

The real upstream is the Bluetooth SIG public repository:

```text
https://bitbucket.org/bluetooth-SIG/public.git
```

The local Git remote is named `up`. `Tools/generate_catalog.py` records the exact upstream commit in the generated resource. GitHub Actions refreshes the snapshot and creates a private weekly `data-YYYY.MM.DD` release.

```bash
python3 Tools/generate_catalog.py --source-repo /path/to/bluetooth-sig-public
python3 -m unittest discover Tools/tests
swift test
```

## Data rights

Package source code and upstream data have separate rights. See [DATA-NOTICE.md](DATA-NOTICE.md). Keep the repository and its data releases private until redistribution rights and product governance have been reviewed.
