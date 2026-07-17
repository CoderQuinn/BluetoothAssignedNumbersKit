import Foundation

public enum BluetoothAssignedNumberKind: String, CaseIterable, Sendable {
    case service
    case characteristic
    case descriptor
}

public struct BluetoothAssignedNumber: Codable, Equatable, Sendable {
    public let uuid: String
    public let name: String
    public let identifier: String?
}

public struct BluetoothAppearance: Codable, Equatable, Sendable {
    public let value: UInt16
    public let category: String
    public let subcategory: String?
}

public struct BluetoothAssignedNumbersMetadata: Equatable, Sendable {
    public let schemaVersion: Int
    public let generatedAt: String
    public let sourceRepository: String
    public let sourceCommit: String
    public let companyIdentifierCount: Int
    public let serviceCount: Int
    public let characteristicCount: Int
    public let descriptorCount: Int
    public let appearanceCount: Int
}

public enum BluetoothAssignedNumbersError: Error, Equatable {
    case resourceMissing
    case malformedResource
}

public final class BluetoothAssignedNumbersCatalog: @unchecked Sendable {
    private struct Source: Codable {
        let repository: String
        let commit: String
    }

    private struct Counts: Codable {
        let companyIdentifiers: Int
        let services: Int
        let characteristics: Int
        let descriptors: Int
        let appearances: Int
    }

    private struct AppearanceRecord: Codable {
        let value: Int
        let category: String
        let subcategory: String?
    }

    private struct Payload: Codable {
        let schemaVersion: Int
        let generatedAt: String
        let source: Source
        let counts: Counts
        let companyIdentifiers: [String: String]
        let services: [String: BluetoothAssignedNumber]
        let characteristics: [String: BluetoothAssignedNumber]
        let descriptors: [String: BluetoothAssignedNumber]
        let appearances: [String: AppearanceRecord]
    }

    private let payload: Payload

    public static func bundled() throws -> BluetoothAssignedNumbersCatalog {
        guard let url = Bundle.module.url(
            forResource: "bluetooth_assigned_numbers",
            withExtension: "json"
        ) else {
            throw BluetoothAssignedNumbersError.resourceMissing
        }
        return try BluetoothAssignedNumbersCatalog(resourceURL: url)
    }

    public init(resourceURL: URL) throws {
        do {
            payload = try JSONDecoder().decode(Payload.self, from: Data(contentsOf: resourceURL))
        } catch {
            throw BluetoothAssignedNumbersError.malformedResource
        }
    }

    public var metadata: BluetoothAssignedNumbersMetadata {
        BluetoothAssignedNumbersMetadata(
            schemaVersion: payload.schemaVersion,
            generatedAt: payload.generatedAt,
            sourceRepository: payload.source.repository,
            sourceCommit: payload.source.commit,
            companyIdentifierCount: payload.counts.companyIdentifiers,
            serviceCount: payload.counts.services,
            characteristicCount: payload.counts.characteristics,
            descriptorCount: payload.counts.descriptors,
            appearanceCount: payload.counts.appearances
        )
    }

    public func companyName(for identifier: UInt16) -> String? {
        payload.companyIdentifiers[String(format: "%04X", identifier)]
    }

    public func companyName(forHex rawValue: String?) -> String? {
        guard let key = Self.normalizedCompanyIdentifier(rawValue) else { return nil }
        return payload.companyIdentifiers[key]
    }

    public func assignedNumber(
        for uuid: String,
        kind: BluetoothAssignedNumberKind
    ) -> BluetoothAssignedNumber? {
        guard let key = Self.normalizedBluetoothUUID(uuid) else { return nil }
        switch kind {
        case .service:
            return payload.services[key]
        case .characteristic:
            return payload.characteristics[key]
        case .descriptor:
            return payload.descriptors[key]
        }
    }

    public func name(for uuid: String, kind: BluetoothAssignedNumberKind) -> String? {
        assignedNumber(for: uuid, kind: kind)?.name
    }

    public func appearance(for value: UInt16) -> BluetoothAppearance? {
        let key = String(format: "%04X", value)
        guard let record = payload.appearances[key],
              let rawValue = UInt16(exactly: record.value)
        else {
            return nil
        }
        return BluetoothAppearance(
            value: rawValue,
            category: record.category,
            subcategory: record.subcategory
        )
    }

    public static func normalizedCompanyIdentifier(_ rawValue: String?) -> String? {
        guard var value = rawValue?.trimmingCharacters(in: .whitespacesAndNewlines),
              !value.isEmpty
        else {
            return nil
        }
        if value.lowercased().hasPrefix("0x") {
            value.removeFirst(2)
        }
        guard value.count <= 4, let identifier = UInt16(value, radix: 16) else { return nil }
        return String(format: "%04X", identifier)
    }

    public static func normalizedBluetoothUUID(_ rawValue: String) -> String? {
        var value = rawValue
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "-", with: "")
            .uppercased()
        if value.hasPrefix("0X") {
            value.removeFirst(2)
        }
        let hexadecimalDigits = CharacterSet(charactersIn: "0123456789ABCDEF")
        guard !value.isEmpty,
              value.unicodeScalars.allSatisfy({ hexadecimalDigits.contains($0) })
        else {
            return nil
        }

        let bluetoothBaseSuffix = "00001000800000805F9B34FB"
        if value.count == 32, value.hasSuffix(bluetoothBaseSuffix) {
            let prefix = String(value.prefix(8))
            if prefix.hasPrefix("0000") {
                return String(prefix.suffix(4))
            }
            return prefix
        }

        guard value.count <= 8 else { return nil }
        let width = value.count <= 4 ? 4 : 8
        guard let number = UInt32(value, radix: 16) else { return nil }
        return String(format: "%0*X", width, number)
    }
}
