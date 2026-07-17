import XCTest
@testable import BluetoothAssignedNumbersKit

final class BluetoothAssignedNumbersCatalogTests: XCTestCase {
    func testBundledCatalogResolvesKnownAssignedNumbers() throws {
        let catalog = try BluetoothAssignedNumbersCatalog.bundled()

        XCTAssertEqual(catalog.companyName(forHex: "0x004c"), "Apple, Inc.")
        XCTAssertEqual(catalog.name(for: "180D", kind: .service), "Heart Rate")
        XCTAssertEqual(
            catalog.name(
                for: "00002A00-0000-1000-8000-00805F9B34FB",
                kind: .characteristic
            ),
            "Device Name"
        )
        XCTAssertEqual(
            catalog.name(for: "2902", kind: .descriptor),
            "Client Characteristic Configuration"
        )
    }

    func testAppearanceUsesFullSixteenBitValue() throws {
        let catalog = try BluetoothAssignedNumbersCatalog.bundled()

        XCTAssertEqual(
            catalog.appearance(for: 0x0040),
            BluetoothAppearance(value: 0x0040, category: "Phone", subcategory: nil)
        )
        XCTAssertEqual(
            catalog.appearance(for: 0x0081),
            BluetoothAppearance(
                value: 0x0081,
                category: "Computer",
                subcategory: "Desktop Workstation"
            )
        )
    }

    func testNormalizationRejectsMalformedValues() {
        XCTAssertEqual(
            BluetoothAssignedNumbersCatalog.normalizedBluetoothUUID("0x180d"),
            "180D"
        )
        XCTAssertNil(BluetoothAssignedNumbersCatalog.normalizedBluetoothUUID("not-a-uuid"))
        XCTAssertNil(BluetoothAssignedNumbersCatalog.normalizedCompanyIdentifier("0x10000"))
    }

    func testBundledMetadataMatchesExpectedScale() throws {
        let metadata = try BluetoothAssignedNumbersCatalog.bundled().metadata

        XCTAssertEqual(metadata.schemaVersion, 1)
        XCTAssertGreaterThan(metadata.companyIdentifierCount, 3_000)
        XCTAssertGreaterThan(metadata.serviceCount, 50)
        XCTAssertGreaterThan(metadata.characteristicCount, 200)
        XCTAssertGreaterThan(metadata.descriptorCount, 10)
        XCTAssertGreaterThan(metadata.appearanceCount, 100)
        XCTAssertEqual(metadata.sourceCommit.count, 40)
    }
}
