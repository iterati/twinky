import { useEffect, useRef, type RefObject } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Layout } from './frame'
import { OVERLAP, unroll } from './unrolled'

export type View = '3d' | 'unrolled'

// A light's glow across: in the 3D view in PointsMaterial's units (half the screen's height, 1 away;
// the tree is 1 high), unrolled in turns round the trunk
const SIZE_3D = 0.06
const SIZE_UNROLLED = 0.035
// How far the camera starts from the trunk
const DISTANCE = 1.9
// One full turn round the tree every 80 seconds
const TURN_SPEED = 0.75

/** A soft round spot, bright in the middle, for each light. */
function glow(): THREE.Texture {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 64
  const context = canvas.getContext('2d')!
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.2, 'rgba(255,255,255,0.8)')
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.15)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, 64, 64)
  return new THREE.CanvasTexture(canvas)
}

function points(positions: Float32Array, colors: Float32Array, material: THREE.PointsMaterial): THREE.Points {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  return new THREE.Points(geometry, material)
}

/** The lights, lit as the last frame has them: round the cone in 3D, or unrolled. */
export default function Tree({
  layout,
  colors,
  view,
}: {
  layout: Layout
  colors: RefObject<Float32Array>
  view: View
}) {
  const host = useRef<HTMLDivElement>(null)
  const shown = useRef(view)
  shown.current = view

  useEffect(() => {
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    host.current!.appendChild(renderer.domElement)

    const map = glow()
    const material = (size: number, sizeAttenuation: boolean) =>
      new THREE.PointsMaterial({
        size,
        sizeAttenuation,
        map,
        vertexColors: true,
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthWrite: false,
      })

    // the 3D view: the tree is 1 high, its trunk on the y axis
    const tree = new THREE.Scene()
    const treeColors = colors.current
    const treeMaterial = material(SIZE_3D, true)
    const cloud = points(new Float32Array(layout.flatMap((l) => [l.x, l.y, l.z])), treeColors, treeMaterial)
    tree.add(cloud)
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100)
    camera.position.set(0, 0.7, DISTANCE)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 0.45, 0)
    controls.enablePan = false
    controls.enableDamping = true
    controls.autoRotate = true
    controls.autoRotateSpeed = TURN_SPEED
    controls.minDistance = 0.5
    controls.maxDistance = 6
    controls.update()

    // the Unrolled view: angle round the trunk across, height up
    const flat = new THREE.Scene()
    const { positions, sources } = unroll(layout)
    const flatColors = new Float32Array(sources.length * 3)
    const flatMaterial = material(1, false)
    const strip = points(positions, flatColors, flatMaterial)
    flat.add(strip)
    // the seam, at both edges of one turn: past each, the strip repeats
    const seams = new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(
        [0, 1].flatMap((x) => [new THREE.Vector3(x, -0.03, 0), new THREE.Vector3(x, 1.03, 0)]),
      ),
      new THREE.LineDashedMaterial({ color: 0x444444, dashSize: 0.02, gapSize: 0.015 }),
    )
    seams.computeLineDistances()
    flat.add(seams)
    const flatCamera = new THREE.OrthographicCamera()

    const resize = () => {
      const width = window.innerWidth
      const height = window.innerHeight
      renderer.setSize(width, height)
      camera.aspect = width / height
      // the lens wide enough for the whole tree, its height on a wide screen and its base on a phone
      const half = Math.max(0.6, 0.5 / camera.aspect)
      camera.fov = (2 * Math.atan(half / DISTANCE) * 180) / Math.PI
      camera.updateProjectionMatrix()
      // the strip filling the screen, from -OVERLAP to 1 + OVERLAP across and 0 to 1 up, with a
      // margin above for the header: a turn and the height have no common unit to keep
      const across = (1 + 2 * OVERLAP) * 1.06
      const up = 1.25
      flatCamera.left = 0.5 - across / 2
      flatCamera.right = 0.5 + across / 2
      flatCamera.bottom = 0.5 - up / 2
      flatCamera.top = 0.5 + up / 2
      flatCamera.position.z = 1
      flatCamera.updateProjectionMatrix()
      flatMaterial.size = SIZE_UNROLLED / Math.max(across / width, up / height)
    }
    resize()
    window.addEventListener('resize', resize)

    const timer = new THREE.Timer()
    renderer.setAnimationLoop((time) => {
      timer.update(time)
      if (shown.current === '3d') {
        cloud.geometry.attributes.color.needsUpdate = true
        controls.update(timer.getDelta())
        renderer.render(tree, camera)
      } else {
        for (let i = 0; i < sources.length; i++) {
          flatColors.set(treeColors.subarray(sources[i] * 3, sources[i] * 3 + 3), i * 3)
        }
        strip.geometry.attributes.color.needsUpdate = true
        renderer.render(flat, flatCamera)
      }
    })

    return () => {
      renderer.setAnimationLoop(null)
      window.removeEventListener('resize', resize)
      controls.dispose()
      cloud.geometry.dispose()
      strip.geometry.dispose()
      seams.geometry.dispose()
      seams.material.dispose()
      treeMaterial.dispose()
      flatMaterial.dispose()
      map.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [layout, colors])

  return <div ref={host} />
}
