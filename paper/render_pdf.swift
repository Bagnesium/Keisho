import AppKit
import CoreGraphics
import CoreText
import Foundation

private let pageWidth: CGFloat = 612
private let pageHeight: CGFloat = 792
private let marginX: CGFloat = 52
private let marginTop: CGFloat = 48
private let marginBottom: CGFloat = 48
private let bodyWidth = pageWidth - 2 * marginX

private enum Block {
    case heading(Int, String)
    case paragraph(String)
    case list(String)
    case caption(String)
    case table([[String]])
}

private func parseMarkdown(_ source: String) -> [Block] {
    let lines = source.components(separatedBy: .newlines)
    var blocks: [Block] = []
    var i = 0
    while i < lines.count {
        let line = lines[i]
        if line.trimmingCharacters(in: .whitespaces).isEmpty {
            i += 1
            continue
        }
        if line.hasPrefix("#"), let match = line.range(of: "^#{1,6}\\s+", options: .regularExpression) {
            let level = line[..<match.upperBound].filter { $0 == "#" }.count
            blocks.append(.heading(level, String(line[match.upperBound...])))
            i += 1
            continue
        }
        if line.trimmingCharacters(in: .whitespaces).hasPrefix("|") {
            var rows: [[String]] = []
            while i < lines.count && lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("|") {
                let cells = lines[i].trimmingCharacters(in: .whitespaces)
                    .split(separator: "|", omittingEmptySubsequences: false)
                    .dropFirst().dropLast().map { String($0).trimmingCharacters(in: .whitespaces) }
                if !cells.allSatisfy({ $0.range(of: "^:?-{3,}:?$", options: .regularExpression) != nil }) {
                    rows.append(cells)
                }
                i += 1
            }
            if !rows.isEmpty { blocks.append(.table(rows)) }
            continue
        }
        if line.range(of: "^\\s*(?:[-*]\\s+|\\d+\\.\\s+)", options: .regularExpression) != nil {
            if let ordered = line.range(of: "^\\s*(\\d+\\.\\s+)", options: .regularExpression) {
                let prefix = String(line[ordered]).trimmingCharacters(in: .whitespaces)
                let content = String(line[ordered.upperBound...])
                blocks.append(.list(prefix + content))
            } else {
                let content = line.replacingOccurrences(of: "^\\s*[-*]\\s+", with: "", options: .regularExpression)
                blocks.append(.list("•  " + content))
            }
            i += 1
            continue
        }
        var paragraph = [line.trimmingCharacters(in: .whitespaces)]
        i += 1
        while i < lines.count {
            let next = lines[i]
            if next.trimmingCharacters(in: .whitespaces).isEmpty || next.hasPrefix("#") || next.trimmingCharacters(in: .whitespaces).hasPrefix("|") || next.range(of: "^\\s*(?:[-*]\\s+|\\d+\\.\\s+)", options: .regularExpression) != nil {
                break
            }
            paragraph.append(next.trimmingCharacters(in: .whitespaces))
            i += 1
        }
        let text = paragraph.joined(separator: " ")
        if text.hasPrefix("**Table ") {
            blocks.append(.caption(text))
        } else {
            blocks.append(.paragraph(text))
        }
    }
    return blocks
}

private func font(_ name: String, _ size: CGFloat) -> NSFont {
    NSFont(name: name, size: size) ?? NSFont.systemFont(ofSize: size)
}

private func richText(_ markdown: String, font baseFont: NSFont, color: NSColor = .black, alignment: NSTextAlignment = .justified, lineSpacing: CGFloat = 1.5, firstIndent: CGFloat = 0, headIndent: CGFloat = 0) -> NSAttributedString {
    let result = NSMutableAttributedString()
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = alignment
    paragraph.lineSpacing = lineSpacing
    paragraph.firstLineHeadIndent = firstIndent
    paragraph.headIndent = headIndent
    paragraph.lineBreakMode = .byWordWrapping
    let baseAttributes: [NSAttributedString.Key: Any] = [.font: baseFont, .foregroundColor: color, .paragraphStyle: paragraph]

    let pattern = "`([^`]+)`|\\*\\*(.+?)\\*\\*|(?<!\\*)\\*([^*]+)\\*(?!\\*)"
    let regex = try! NSRegularExpression(pattern: pattern)
    let ns = markdown as NSString
    let matches = regex.matches(in: markdown, range: NSRange(location: 0, length: ns.length))
    var cursor = 0
    for match in matches {
        if match.range.location > cursor {
            result.append(NSAttributedString(string: ns.substring(with: NSRange(location: cursor, length: match.range.location - cursor)), attributes: baseAttributes))
        }
        var contentRange = match.range(at: 1)
        var chosenFont = baseFont
        if contentRange.location == NSNotFound {
            contentRange = match.range(at: 2)
            if contentRange.location != NSNotFound {
                chosenFont = NSFontManager.shared.convert(baseFont, toHaveTrait: .boldFontMask)
            } else {
                contentRange = match.range(at: 3)
                chosenFont = NSFontManager.shared.convert(baseFont, toHaveTrait: .italicFontMask)
            }
        } else {
            chosenFont = font("Courier", max(7, baseFont.pointSize - 1.1))
        }
        var attrs = baseAttributes
        attrs[.font] = chosenFont
        if chosenFont.fontName.contains("Courier") { attrs[.foregroundColor] = NSColor(calibratedRed: 0.12, green: 0.18, blue: 0.25, alpha: 1) }
        result.append(NSAttributedString(string: ns.substring(with: contentRange), attributes: attrs))
        cursor = NSMaxRange(match.range)
    }
    if cursor < ns.length {
        result.append(NSAttributedString(string: ns.substring(from: cursor), attributes: baseAttributes))
    }
    return result
}

private func textHeight(_ text: NSAttributedString, width: CGFloat) -> CGFloat {
    let framesetter = CTFramesetterCreateWithAttributedString(text as CFAttributedString)
    var fit = CFRange()
    let size = CTFramesetterSuggestFrameSizeWithConstraints(framesetter, CFRange(location: 0, length: text.length), nil, CGSize(width: width, height: 10000), &fit)
    return max(10, ceil(size.height + 2))
}

private func drawText(_ text: NSAttributedString, x: CGFloat, top: CGFloat, width: CGFloat, height: CGFloat, in context: CGContext) {
    context.saveGState()
    context.textMatrix = .identity
    let path = CGPath(rect: CGRect(x: x, y: pageHeight - top - height, width: width, height: height), transform: nil)
    let framesetter = CTFramesetterCreateWithAttributedString(text as CFAttributedString)
    let frame = CTFramesetterCreateFrame(framesetter, CFRange(location: 0, length: text.length), path, nil)
    CTFrameDraw(frame, context)
    context.restoreGState()
}

private final class PDFLayout {
    let context: CGContext
    var top = marginTop
    var pageNumber = 0

    init(output: URL) throws {
        var mediaBox = CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight)
        guard let cg = CGContext(output as CFURL, mediaBox: &mediaBox, nil) else {
            throw NSError(domain: "ManuscriptPDF", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not create PDF context"])
        }
        context = cg
        beginPage()
    }

    private func beginPage() {
        pageNumber += 1
        context.beginPDFPage(nil)
        top = marginTop
    }

    private func endPage() {
        let footer = richText("\(pageNumber)", font: font("Times-Roman", 8), color: NSColor.darkGray, alignment: .center, lineSpacing: 0)
        drawText(footer, x: marginX, top: pageHeight - marginBottom + 15, width: bodyWidth, height: 16, in: context)
        context.endPDFPage()
    }

    private func nextPage() {
        endPage()
        beginPage()
    }

    func addHeading(level: Int, text: String) {
        if level == 1 {
            let title = richText(text, font: font("Times-Bold", 17.5), alignment: .center, lineSpacing: 0)
            let height = textHeight(title, width: bodyWidth)
            if top + height + 28 > pageHeight - marginBottom { nextPage() }
            drawText(title, x: marginX, top: top, width: bodyWidth, height: height + 5, in: context)
            top += height + 12
        } else {
            let size: CGFloat = level == 2 ? 13.2 : 11.1
            let head = richText(text, font: font("Times-Bold", size), alignment: .left, lineSpacing: 0)
            let height = textHeight(head, width: bodyWidth)
            let gapBefore: CGFloat = level == 2 ? 10 : 6
            let gapAfter: CGFloat = 3
            if top + gapBefore + height + gapAfter + 36 > pageHeight - marginBottom { nextPage() }
            top += gapBefore
            drawText(head, x: marginX, top: top, width: bodyWidth, height: height + 3, in: context)
            top += height + gapAfter
        }
    }

    func addParagraph(_ text: String, byline: Bool = false, metadata: Bool = false, keywords: Bool = false) {
        let chosenFont = byline ? font("Times-Bold", 10.5) : (metadata ? font("Times-Italic", 9.2) : font("Times-Roman", 10.2))
        let alignment: NSTextAlignment = (byline || metadata || keywords) ? .center : .justified
        let para = richText(text, font: chosenFont, alignment: alignment, lineSpacing: byline || metadata || keywords ? 0.5 : 1.4)
        let height = textHeight(para, width: bodyWidth)
        if top + height + 7 > pageHeight - marginBottom { nextPage() }
        drawText(para, x: marginX, top: top, width: bodyWidth, height: height + 4, in: context)
        top += height + (keywords ? 13 : 6)
    }

    func addList(_ text: String) {
        let para = richText(text, font: font("Times-Roman", 9.2), alignment: .left, lineSpacing: 0.6, firstIndent: 0, headIndent: 15)
        let height = textHeight(para, width: bodyWidth - 10)
        if top + height + 2 > pageHeight - marginBottom { nextPage() }
        drawText(para, x: marginX + 10, top: top, width: bodyWidth - 10, height: height + 3, in: context)
        top += height + 2
    }

    func addTable(_ rows: [[String]], caption: String?) {
        let columns = rows.map(\.count).max() ?? 0
        guard columns > 0 else { return }
        var weights: [CGFloat]
        if columns == 7 {
            weights = [1.7, 0.83, 0.66, 0.66, 1.16, 1.08, 0.91]
        } else if columns == 6 {
            weights = [0.42, 0.66, 2.65, 0.83, 0.94, 0.92]
        } else {
            weights = Array(repeating: 1, count: columns)
        }
        if weights.count != columns { weights = Array(repeating: 1, count: columns) }
        let sum = weights.reduce(0, +)
        let widths = weights.map { bodyWidth * $0 / sum }
        let cellFont = font("Times-Roman", columns >= 6 ? 7.3 : 8)
        let headerFont = font("Times-Bold", columns >= 6 ? 7.4 : 8.1)

        let preparedRows: [([NSAttributedString], CGFloat)] = rows.enumerated().map { rowIndex, row in
            let strings = (0..<columns).map { col -> NSAttributedString in
                let raw = col < row.count ? row[col] : ""
                return richText(raw, font: rowIndex == 0 ? headerFont : cellFont, alignment: .left, lineSpacing: 0.4)
            }
            let heights = strings.enumerated().map { index, value in textHeight(value, width: max(10, widths[index] - 8)) }
            return (strings, max(18, (heights.max() ?? 12) + 7))
        }
        let captionText = caption.map { richText($0, font: font("Times-Roman", 9.2), alignment: .left, lineSpacing: 0.8) }
        let captionHeight = captionText.map { textHeight($0, width: bodyWidth) + 4 } ?? 0
        let tableHeight = preparedRows.reduce(CGFloat(0)) { $0 + $1.1 } + captionHeight + 8
        if top + tableHeight > pageHeight - marginBottom && tableHeight < pageHeight - marginTop - marginBottom {
            nextPage()
        }
        if let captionText {
            drawText(captionText, x: marginX, top: top, width: bodyWidth, height: captionHeight, in: context)
            top += captionHeight
        }

        for (rowIndex, item) in preparedRows.enumerated() {
            let (strings, rowHeight) = item
            if top + rowHeight + 12 > pageHeight - marginBottom {
                nextPage()
            }
            var x = marginX
            let pdfRect = CGRect(x: marginX, y: pageHeight - top - rowHeight, width: bodyWidth, height: rowHeight)
            if rowIndex == 0 {
                context.setFillColor(NSColor(calibratedWhite: 0.91, alpha: 1).cgColor)
                context.fill(pdfRect)
            }
            context.setStrokeColor(NSColor(calibratedWhite: 0.42, alpha: 1).cgColor)
            context.setLineWidth(0.45)
            context.stroke(pdfRect)
            for column in 0..<columns {
                let cellRect = CGRect(x: x, y: pageHeight - top - rowHeight, width: widths[column], height: rowHeight)
                context.stroke(cellRect)
                drawText(strings[column], x: x + 4, top: top + 3, width: widths[column] - 8, height: rowHeight - 5, in: context)
                x += widths[column]
            }
            top += rowHeight
        }
        top += 8
    }

    func finish() {
        endPage()
        context.closePDF()
    }
}

private func run() throws {
    let directory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    let input = directory.appendingPathComponent("MANUSCRIPT_FINAL_PILOT.md")
    let output = directory.appendingPathComponent("MANUSCRIPT_FINAL_PILOT.pdf")
    let source = try String(contentsOf: input, encoding: .utf8)
    let blocks = parseMarkdown(source)
    let layout = try PDFLayout(output: output)
    var openingParagraphs = 0
    var titleSeen = false
    var pendingCaption: String? = nil
    for block in blocks {
        switch block {
        case let .heading(level, text):
            layout.addHeading(level: level, text: text)
            if level == 1 && !titleSeen { titleSeen = true }
        case let .paragraph(text):
            if titleSeen && openingParagraphs < 3 {
                layout.addParagraph(text, byline: openingParagraphs == 0, metadata: openingParagraphs == 1, keywords: openingParagraphs == 2)
                openingParagraphs += 1
            } else {
                layout.addParagraph(text)
            }
        case let .list(text):
            layout.addList(text)
        case let .caption(text):
            pendingCaption = text
        case let .table(rows):
            layout.addTable(rows, caption: pendingCaption)
            pendingCaption = nil
        }
    }
    layout.finish()
    print("Wrote \(output.path)")
}

do {
    try run()
} catch {
    fputs("PDF generation failed: \(error)\n", stderr)
    exit(1)
}
