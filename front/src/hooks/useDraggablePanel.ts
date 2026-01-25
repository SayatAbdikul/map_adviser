import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';

type Anchor = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

type InitialPosition =
  | { x: number; y: number }
  | { anchor: Anchor; offset?: number };

type DragPosition = { x: number; y: number };

type DragState = {
  startX: number;
  startY: number;
  originX: number;
  originY: number;
  moved: boolean;
};

type DraggablePanelOptions = {
  boundsPadding?: number;
  dragThreshold?: number;
};

export const useDraggablePanel = (
  initialPosition: InitialPosition,
  options: DraggablePanelOptions = {}
) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<DragState | null>(null);
  const [position, setPosition] = useState<DragPosition | null>(null);
  const positionRef = useRef<DragPosition | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const boundsPadding = options.boundsPadding ?? 12;
  const dragThreshold = options.dragThreshold ?? 4;

  const clampPosition = useCallback(
    (next: DragPosition) => {
      const panel = panelRef.current;
      const rect = panel?.getBoundingClientRect();
      const maxX = rect ? window.innerWidth - rect.width - boundsPadding : undefined;
      const maxY = rect ? window.innerHeight - rect.height - boundsPadding : undefined;
      const clampedX = Math.min(Math.max(next.x, boundsPadding), Math.max(boundsPadding, maxX ?? next.x));
      const clampedY = Math.min(Math.max(next.y, boundsPadding), Math.max(boundsPadding, maxY ?? next.y));
      const clamped = { x: clampedX, y: clampedY };

      setPosition((prev) => {
        if (prev && prev.x === clamped.x && prev.y === clamped.y) return prev;
        return clamped;
      });
    },
    [boundsPadding]
  );

  useLayoutEffect(() => {
    if (position !== null) return;
    const panel = panelRef.current;
    if (!panel) return;
    const rect = panel.getBoundingClientRect();
    let next: DragPosition;
    if ('x' in initialPosition) {
      next = { x: initialPosition.x, y: initialPosition.y };
    } else {
      const offset = initialPosition.offset ?? 16;
      switch (initialPosition.anchor) {
        case 'top-left':
          next = { x: offset, y: offset };
          break;
        case 'top-right':
          next = { x: window.innerWidth - rect.width - offset, y: offset };
          break;
        case 'bottom-left':
          next = { x: offset, y: window.innerHeight - rect.height - offset };
          break;
        case 'bottom-right':
        default:
          next = { x: window.innerWidth - rect.width - offset, y: window.innerHeight - rect.height - offset };
          break;
      }
    }
    clampPosition(next);
  }, [position, initialPosition, clampPosition]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMove = (event: PointerEvent) => {
      const dragState = dragStateRef.current;
      if (!dragState) return;
      const deltaX = event.clientX - dragState.startX;
      const deltaY = event.clientY - dragState.startY;
      if (!dragState.moved && Math.hypot(deltaX, deltaY) > dragThreshold) {
        dragState.moved = true;
      }
      clampPosition({ x: dragState.originX + deltaX, y: dragState.originY + deltaY });
    };

    const handleUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, [isDragging, clampPosition, dragThreshold]);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  useEffect(() => {
    const handleResize = () => {
      if (positionRef.current) {
        clampPosition(positionRef.current);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [clampPosition]);

  const startDrag = useCallback(
    (event: ReactPointerEvent) => {
      if (event.button !== 0) return;
      if (position === null) return;
      event.preventDefault();
      dragStateRef.current = {
        startX: event.clientX,
        startY: event.clientY,
        originX: position.x,
        originY: position.y,
        moved: false,
      };
      setIsDragging(true);
    },
    [position]
  );

  const didDrag = useCallback(() => dragStateRef.current?.moved ?? false, []);

  const ensureInView = useCallback(() => {
    const current = positionRef.current;
    if (!current) return;
    clampPosition(current);
  }, [clampPosition]);

  return {
    panelRef,
    position,
    startDrag,
    didDrag,
    ensureInView,
  };
};
