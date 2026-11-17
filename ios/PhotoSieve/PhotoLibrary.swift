import Photos
import UIKit

@MainActor
final class PhotoLibrary {
    private let manager = PHImageManager()

    func requestAccess() async throws -> PHAuthorizationStatus {
        let status = await PHPhotoLibrary.requestAuthorization(for: .readWrite)
        guard status == .authorized || status == .limited else {
            throw SieveError.message("Allow Photos access in Settings to scan and delete selected photos.")
        }
        return status
    }

    func assets(limit: Int) -> [PHAsset] {
        let options = PHFetchOptions()
        options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
        options.fetchLimit = limit
        let fetched = PHAsset.fetchAssets(with: .image, options: options)
        var result: [PHAsset] = []
        fetched.enumerateObjects { asset, _, _ in result.append(asset) }
        return result
    }

    func thumbnail(for asset: PHAsset, size: CGFloat = 512) async -> UIImage? {
        let imageManager = manager
        return await withCheckedContinuation { continuation in
            // Synchronous PhotoKit requests give exactly one callback. A dedicated
            // background queue avoids blocking the UI and double-resuming continuations
            // when PhotoKit would otherwise deliver degraded and final images.
            DispatchQueue.global(qos: .userInitiated).async {
                let options = PHImageRequestOptions()
                options.isSynchronous = true
                options.deliveryMode = .highQualityFormat
                options.resizeMode = .fast
                // Local-only scan: iCloud-only assets are counted as unavailable.
                options.isNetworkAccessAllowed = false
                imageManager.requestImage(
                    for: asset, targetSize: CGSize(width: size, height: size),
                    contentMode: .aspectFit, options: options
                ) { image, _ in continuation.resume(returning: image) }
            }
        }
    }

    func delete(ids: Set<String>) async throws {
        guard !ids.isEmpty else { return }
        let status = PHPhotoLibrary.authorizationStatus(for: .readWrite)
        guard status == .authorized || status == .limited else {
            throw SieveError.message("Photos permission changed. Scan again after granting access.")
        }
        // Re-fetch immediately before deletion: assets may have changed since scanning.
        let fetched = PHAsset.fetchAssets(withLocalIdentifiers: Array(ids), options: nil)
        guard fetched.count == ids.count else {
            throw SieveError.message("Some selected photos are no longer accessible. Scan again.")
        }
        var current: [PHAsset] = []
        fetched.enumerateObjects { asset, _, _ in current.append(asset) }
        guard current.allSatisfy({ $0.canPerform(.delete) }) else {
            throw SieveError.message("A selected photo cannot be deleted, for example a computer-synced photo.")
        }
        try await PHPhotoLibrary.shared().performChanges {
            PHAssetChangeRequest.deleteAssets(fetched)
        }
    }
}
