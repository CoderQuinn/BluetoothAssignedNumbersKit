// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "BluetoothAssignedNumbersKit",
    platforms: [.iOS(.v15), .macOS(.v12)],
    products: [
        .library(
            name: "BluetoothAssignedNumbersKit",
            targets: ["BluetoothAssignedNumbersKit"]
        ),
    ],
    targets: [
        .target(
            name: "BluetoothAssignedNumbersKit",
            resources: [.process("Data")]
        ),
        .testTarget(
            name: "BluetoothAssignedNumbersKitTests",
            dependencies: ["BluetoothAssignedNumbersKit"]
        ),
    ]
)
