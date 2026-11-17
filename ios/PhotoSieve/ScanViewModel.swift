import Photos
import SwiftUI

struct PhotoMatch: Identifiable {
    let id: String
    let thumbnail: UIImage
    let score: Double
    let prompt: String
    let candidate: Bool
    let canDelete: Bool
}

@MainActor
final class ScanViewModel: ObservableObject {
    @Published var address = "http://My-Mac.local:8765"
    @Published var token = "" // Memory only; never UserDefaults or a source file.
    @Published var descriptions = "a bowl of ramen"
    @Published var keepDescriptions = ""
    @Published var threshold = 0.25
    @Published var margin = 0.02
    @Published var limit = 100
    @Published var matches: [PhotoMatch] = []
    @Published var selected: Set<String> = []
    @Published var busy = false
    @Published var deleting = false
    @Published var progress = "Ready. Start with a small scan."
    @Published var error: String?
    @Published var limitedAccess = false
    @Published var scanned = 0
    @Published var skipped = 0
    @Published var total = 0
    private let library = PhotoLibrary()
    private var scanTask: Task<Void, Never>?
    private let reviewLimit = 200

    var candidates: [PhotoMatch] { matches.filter(\.candidate) }

    private func lines(_ text: String) -> [String] {
        var seen = Set<String>()
        return text.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty && seen.insert($0).inserted }
    }

    func start() {
        guard !busy && !deleting else { return }
        let prompts = lines(descriptions)
        let keep = lines(keepDescriptions)
        guard !prompts.isEmpty, prompts.count <= 12, keep.count <= 12,
              (prompts + keep).allSatisfy({ $0.count <= 240 }) else {
            error = "Enter 1–12 descriptions, at most 240 characters each. Keep descriptions are optional."
            return
        }
        let client: EngineClient
        do { client = try EngineClient(address: address, token: token) }
        catch { self.error = error.localizedDescription; return }
        let scanThreshold = threshold
        let scanMargin = margin
        let scanLimit = limit
        busy = true
        error = nil
        matches = []
        selected = []
        scanned = 0
        skipped = 0
        total = 0
        progress = "Connecting to your Mac…"
        scanTask = Task {
            defer { busy = false; scanTask = nil }
            do {
                try await client.checkConnection()
                let status = try await library.requestAccess()
                limitedAccess = status == .limited
                let assets = library.assets(limit: scanLimit)
                total = assets.count
                for asset in assets {
                    try Task.checkCancellation()
                    progress = "Scanning \(scanned + skipped + 1) of \(total)…"
                    guard let image = await library.thumbnail(for: asset),
                          let jpeg = image.jpegData(compressionQuality: 0.75) else {
                        skipped += 1
                        continue
                    }
                    try Task.checkCancellation()
                    let result = try await client.score(
                        jpeg: jpeg, prompts: prompts, keep: keep,
                        threshold: scanThreshold, margin: scanMargin
                    )
                    try Task.checkCancellation()
                    scanned += 1
                    matches.append(PhotoMatch(
                        id: asset.localIdentifier, thumbnail: image, score: result.score,
                        prompt: result.bestPrompt, candidate: result.candidate,
                        canDelete: asset.canPerform(.delete)
                    ))
                    // Keep at most 200 thumbnails in RAM. Review emphasizes candidates,
                    // then ranks by similarity. No selection is automatic.
                    matches.sort {
                        if $0.candidate != $1.candidate { return $0.candidate }
                        return $0.score > $1.score
                    }
                    if matches.count > reviewLimit { matches.removeLast() }
                }
                progress = "Scored \(scanned); unavailable locally \(skipped). Showing up to \(reviewLimit) results."
            } catch is CancellationError {
                progress = "Scan stopped. Partial results can be reviewed."
            } catch {
                if Task.isCancelled {
                    progress = "Scan stopped. Partial results can be reviewed."
                } else {
                    self.error = error.localizedDescription
                    progress = "Scan stopped after \(scanned) scores. Partial results kept."
                }
            }
        }
    }

    func stop() { scanTask?.cancel() }

    func toggle(_ match: PhotoMatch) {
        guard !busy && !deleting && match.canDelete else { return }
        if selected.contains(match.id) { selected.remove(match.id) }
        else { selected.insert(match.id) }
    }

    func clearSelection() { selected = [] }

    func deleteSelected() async {
        guard !busy && !deleting && !selected.isEmpty else { return }
        let approved = selected
        guard approved.isSubset(of: Set(matches.filter(\.canDelete).map(\.id))) else {
            error = "Selection changed. Review your photos again."
            return
        }
        deleting = true
        defer { deleting = false }
        do {
            try await library.delete(ids: approved)
            matches.removeAll { approved.contains($0.id) }
            selected.subtract(approved)
            progress = "Deleted \(approved.count) photos. Recovery is available in Photos → Recently Deleted."
        } catch {
            self.error = error.localizedDescription
        }
    }
}
