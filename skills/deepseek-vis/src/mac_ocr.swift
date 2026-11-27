import Foundation
import Vision
import AppKit

struct RecognizedItem: Codable {
    let text: String
    let confidence: Float
    let bbox: [Double] // [left, top, width, height] normalized 0.0 - 1.0
}

guard CommandLine.arguments.count > 1 else {
    fputs("Usage: mac_ocr <image-path>\n", stderr)
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard let nsImage = NSImage(contentsOf: imageURL),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Error: Could not load image at \(imagePath)\n", stderr)
    exit(1)
}

let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

var resultsList: [RecognizedItem] = []

do {
    try requestHandler.perform([request])
    if let results = request.results {
        for observation in results {
            guard let topCandidate = observation.topCandidates(1).first else { continue }
            let box = observation.boundingBox
            // Vision bbox origin is bottom-left (0,0). Convert to top-left (0,0).
            let left = box.origin.x
            let top = 1.0 - (box.origin.y + box.size.height)
            let width = box.size.width
            let height = box.size.height
            
            let item = RecognizedItem(
                text: topCandidate.string,
                confidence: topCandidate.confidence,
                bbox: [left, top, width, height]
            )
            resultsList.append(item)
        }
    }
    
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let jsonData = try encoder.encode(resultsList)
    if let jsonString = String(data: jsonData, encoding: .utf8) {
        print(jsonString)
    }
} catch {
    fputs("Error performing OCR: \(error.localizedDescription)\n", stderr)
    exit(1)
}
