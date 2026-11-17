import SwiftUI

struct ContentView: View {
    @StateObject private var model = ScanViewModel()
    @State private var showDeleteConfirmation = false
    @State private var candidatesOnly = true
    private let columns = [GridItem(.adaptive(minimum: 145), spacing: 12)]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Find by words. Review with care.")
                        .font(.title2.bold())
                    Text("Your iPhone reads Photos. Your Mac scores thumbnails over local Wi-Fi. You choose what gets deleted.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    connection
                    scanSettings
                    scanControls
                    review
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Photo Sieve")
            .safeAreaInset(edge: .bottom) { deleteBar }
            .alert("Photo Sieve", isPresented: Binding(
                get: { model.error != nil }, set: { if !$0 { model.error = nil } }
            )) { Button("OK") { model.error = nil } }
            message: { Text(model.error ?? "") }
            .confirmationDialog(
                "Delete \(model.selected.count) selected photos?",
                isPresented: $showDeleteConfirmation, titleVisibility: .visible
            ) {
                Button("Delete \(model.selected.count) photos", role: .destructive) {
                    Task { await model.deleteSelected() }
                }
            } message: {
                Text("This deletes originals from Photos, including the entire Live Photo. With iCloud Photos, deletion syncs to your other devices. Photos normally keeps them in Recently Deleted for 30 days. Apple will ask for permission.")
            }
        }
        .tint(.green)
    }

    private var connection: some View {
        GroupBox("1 · Connect your Mac") {
            VStack(alignment: .leading, spacing: 12) {
                TextField("http://My-Mac.local:8765", text: $model.address)
                    .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                    .textFieldStyle(.roundedBorder)
                SecureField("Pairing token from Mac terminal", text: $model.token)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                    .textFieldStyle(.roundedBorder)
                Text("Use trusted private Wi-Fi. Prototype traffic is local HTTP, without encryption. Tokens stay in memory.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(.top, 8)
        }.disabled(model.busy || model.deleting)
    }

    private var scanSettings: some View {
        GroupBox("2 · Describe what to find") {
            VStack(alignment: .leading, spacing: 12) {
                Text("One description per line; any can match.").font(.caption)
                TextEditor(text: $model.descriptions).frame(minHeight: 75)
                    .scrollContentBackground(.hidden).background(Color(.secondarySystemBackground))
                DisclosureGroup("Optional keep descriptions and tuning") {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Keep descriptions are visual comparisons, not a guarantee.").font(.caption)
                        TextEditor(text: $model.keepDescriptions).frame(height: 65)
                        Text("Minimum similarity: \(model.threshold, specifier: "%.2f")")
                        Slider(value: $model.threshold, in: 0...0.5, step: 0.01)
                        Text("Lead over keep descriptions: \(model.margin, specifier: "%.2f")")
                        Slider(value: $model.margin, in: 0...0.2, step: 0.01)
                        Text("Scores rank similarity; 0.25 is an uncalibrated starting point, not 25% confidence.")
                            .font(.caption).foregroundStyle(.secondary)
                    }.padding(.top, 8)
                }
                Picker("Newest photos", selection: $model.limit) {
                    Text("100").tag(100)
                    Text("500").tag(500)
                    Text("All").tag(0)
                }.pickerStyle(.segmented)
                Text("Reads accessible images only. iCloud downloads are disabled; videos and hidden photos are excluded by the default fetch.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(.top, 8)
        }.disabled(model.busy || model.deleting)
    }

    private var scanControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            if model.busy {
                ProgressView(value: Double(model.scanned + model.skipped), total: Double(max(1, model.total)))
                Button("Stop scan", role: .cancel) { model.stop() }
                    .buttonStyle(.bordered)
            } else {
                Button { model.start() } label: {
                    Label("Scan photos", systemImage: "sparkle.magnifyingglass").frame(maxWidth: .infinity)
                }.buttonStyle(.borderedProminent).disabled(model.deleting)
            }
            Text(model.progress).font(.caption).accessibilityLabel(model.progress)
            if model.limitedAccess {
                Text("Limited Photos access: only photos you allowed are scanned. Change access in Settings to include more.")
                    .font(.caption).foregroundStyle(.orange)
            }
        }
    }

    private var review: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("3 · Review matches").font(.headline)
            Toggle("Show candidates only", isOn: $candidatesOnly)
            Text("Tap photos to select them. Nothing is selected automatically. Up to 200 ranked results are retained per scan.")
                .font(.caption).foregroundStyle(.secondary)
            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(candidatesOnly ? model.candidates : model.matches) { match in
                    Button { model.toggle(match) } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            Image(uiImage: match.thumbnail).resizable().scaledToFit()
                                .frame(height: 145).frame(maxWidth: .infinity)
                                .background(Color(.secondarySystemBackground))
                                .overlay(alignment: .topTrailing) {
                                    Image(systemName: model.selected.contains(match.id) ? "checkmark.circle.fill" : "circle")
                                        .font(.title2).foregroundStyle(.green).padding(6)
                                }
                            Text(match.prompt).font(.caption).lineLimit(2)
                            Text("Similarity \(match.score, specifier: "%.3f")").font(.caption2)
                            if !match.canDelete { Text("Cannot delete").font(.caption2).foregroundStyle(.orange) }
                        }.padding(8).background(.background, in: RoundedRectangle(cornerRadius: 12))
                    }.buttonStyle(.plain).disabled(model.busy || model.deleting || !match.canDelete)
                    .accessibilityLabel("\(match.prompt), similarity \(match.score), \(model.selected.contains(match.id) ? "selected" : "not selected")")
                }
            }
            if !model.busy && model.matches.isEmpty {
                Text("Scan a small sample first. If no candidates appear, turn off the candidate filter and inspect the ranking.")
                    .foregroundStyle(.secondary).font(.subheadline)
            }
        }
    }

    private var deleteBar: some View {
        HStack {
            Button("Clear") { model.clearSelection() }.disabled(model.busy || model.deleting)
            Spacer()
            Button(role: .destructive) { showDeleteConfirmation = true } label: {
                Label(model.deleting ? "Deleting…" : "Delete selected (\(model.selected.count))", systemImage: "trash")
            }.buttonStyle(.borderedProminent)
                .disabled(model.selected.isEmpty || model.busy || model.deleting)
        }.padding().background(.ultraThinMaterial)
    }
}
