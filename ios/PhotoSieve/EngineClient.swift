import Foundation

struct ScoreResponse: Decodable {
    let apiVersion: Int
    let score: Double
    let bestPrompt: String
    let keepScore: Double?
    let candidate: Bool
    let model: String

    enum CodingKeys: String, CodingKey {
        case apiVersion = "api_version"
        case bestPrompt = "best_prompt"
        case keepScore = "keep_score"
        case score, candidate, model
    }
}

enum SieveError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        switch self { case .message(let text): return text }
    }
}

// A URLSession with no on-disk response cache, cookies, or redirects. A pairing
// bearer token must never follow a redirect to another machine.
final class NoRedirects: NSObject, URLSessionTaskDelegate {
    func urlSession(
        _ session: URLSession, task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) { completionHandler(nil) }
}

final class EngineClient {
    private let baseURL: URL
    private let token: String
    private let session: URLSession

    init(address: String, token: String) throws {
        guard let url = URL(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              url.scheme == "http", let host = url.host,
              url.user == nil, url.password == nil, url.query == nil, url.fragment == nil,
              url.path.isEmpty || url.path == "/", Self.isLocalHost(host)
        else {
            throw SieveError.message("Use your Mac’s local address, e.g. http://My-Mac.local:8765")
        }
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 24, trimmed.utf8.allSatisfy({ $0 >= 33 && $0 <= 126 }) else {
            throw SieveError.message("Paste the pairing token from your Mac terminal.")
        }
        baseURL = url
        self.token = trimmed
        let config = URLSessionConfiguration.ephemeral
        config.urlCache = nil
        config.httpCookieStorage = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        config.timeoutIntervalForRequest = 90
        config.timeoutIntervalForResource = 120
        session = URLSession(configuration: config, delegate: NoRedirects(), delegateQueue: nil)
    }

    deinit { session.invalidateAndCancel() }

    static func isLocalHost(_ host: String) -> Bool {
        if host.lowercased().hasSuffix(".local") || host == "localhost" { return true }
        let pieces = host.split(separator: ".", omittingEmptySubsequences: false)
        guard pieces.count == 4 else { return false }
        let numbers = pieces.compactMap { Int($0) }
        guard numbers.count == 4, numbers.allSatisfy({ (0...255).contains($0) }) else { return false }
        return numbers[0] == 10 || numbers[0] == 127
            || (numbers[0] == 192 && numbers[1] == 168)
            || (numbers[0] == 172 && (16...31).contains(numbers[1]))
    }

    private func send(path: String, body: Data? = nil) async throws -> Data {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let message = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            throw SieveError.message(message?["error"] as? String ?? "Mac engine did not respond successfully.")
        }
        return data
    }

    func checkConnection() async throws {
        let data = try await send(path: "v1/health")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard json?["api_version"] as? Int == 1, json?["status"] as? String == "ready" else {
            throw SieveError.message("Incompatible Mac engine. Update both app and engine.")
        }
    }

    func score(jpeg: Data, prompts: [String], keep: [String], threshold: Double, margin: Double) async throws -> ScoreResponse {
        let payload: [String: Any] = [
            "api_version": 1, "image_base64": jpeg.base64EncodedString(),
            "prompts": prompts, "exclude_prompts": keep, "threshold": threshold, "margin": margin
        ]
        let data = try await send(path: "v1/score", body: JSONSerialization.data(withJSONObject: payload))
        let result = try JSONDecoder().decode(ScoreResponse.self, from: data)
        guard result.apiVersion == 1, result.score.isFinite, (-1.0...1.0).contains(result.score) else {
            throw SieveError.message("Engine returned an invalid score.")
        }
        return result
    }
}
