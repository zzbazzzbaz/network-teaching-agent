const IMAGE_MARKER = /^\[图片\] (.+?) \(file_id=([0-9a-fA-F-]{36})\)$/

export interface ImageMarker {
  fileId: string
  name: string
}

export function parseImageMarkers(text: string): {
  text: string
  images: ImageMarker[]
} {
  const images: ImageMarker[] = []
  const lines: string[] = []
  for (const line of text.split("\n")) {
    const match = IMAGE_MARKER.exec(line.trim())
    if (match) {
      images.push({ name: match[1], fileId: match[2] })
    } else {
      lines.push(line)
    }
  }
  return { text: lines.join("\n").trim(), images }
}
