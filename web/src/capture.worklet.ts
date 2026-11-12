// On the audio thread: hands the page its input's sound, mixed to one channel, 512 samples at a time

declare class AudioWorkletProcessor {
  readonly port: MessagePort
}
declare function registerProcessor(name: string, processor: typeof AudioWorkletProcessor): void

const BLOCK = 512

class Capture extends AudioWorkletProcessor {
  private block = new Float32Array(BLOCK)
  private filled = 0

  process(inputs: Float32Array[][]): boolean {
    const channels = inputs[0]
    const length = channels.length ? channels[0].length : 0
    for (let i = 0; i < length; i++) {
      let sum = 0
      for (const channel of channels) sum += channel[i]
      this.block[this.filled++] = sum / channels.length
      if (this.filled === BLOCK) {
        this.port.postMessage(this.block, [this.block.buffer])
        this.block = new Float32Array(BLOCK)
        this.filled = 0
      }
    }
    return true
  }
}

registerProcessor('capture', Capture)

export {}
