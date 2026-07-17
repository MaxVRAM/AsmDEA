import { Position } from '@xyflow/react'

// A LR/RL layout flows horizontally; TB/BT flows vertically. Used to decide
// which axis the external-dependency column stacks along.
export const isHorizontal = (direction) => direction === 'LR' || direction === 'RL'

// Source/target handle sides for a given flow direction. The "source" is the
// upstream (depends-on) end, the "target" is the dependency end; edges are
// drawn source → target, so the target handle faces back toward the source.
export function handlePositions(direction) {
  switch (direction) {
    case 'RL': return { sourcePosition: Position.Left, targetPosition: Position.Right }
    case 'TB': return { sourcePosition: Position.Bottom, targetPosition: Position.Top }
    case 'BT': return { sourcePosition: Position.Top, targetPosition: Position.Bottom }
    case 'LR':
    default: return { sourcePosition: Position.Right, targetPosition: Position.Left }
  }
}
