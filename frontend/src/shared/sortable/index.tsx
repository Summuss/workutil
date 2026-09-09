import {
  closestCenter,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type Active,
  type CollisionDetection,
  type DragCancelEvent,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type SensorDescriptor,
} from "@dnd-kit/core";
import {
  sortableKeyboardCoordinates,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  type SortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import React, {
  createContext,
  useContext,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type ReactNode,
} from "react";

import { DragHandleIcon } from "../icons";

export const IsOverlayContext = createContext<boolean>(false);

export function useIsOverlay(): boolean {
  return useContext(IsOverlayContext);
}

export function useDefaultSensors() {
  return useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 3,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
}

export interface SortableContainerProps {
  sensors?: SensorDescriptor<any>[];
  collisionDetection?: CollisionDetection;
  onDragStart?: (event: DragStartEvent) => void;
  onDragOver?: (event: DragOverEvent) => void;
  onDragEnd?: (event: DragEndEvent) => void;
  onDragCancel?: (event: DragCancelEvent) => void;
  renderOverlay?: (active: Active) => ReactNode;
  children: ReactNode;
}

/**
 * Top-level container providing DndContext + DragOverlay with portal rendering.
 * Used when multiple sortable sub-lists share a single drag context (e.g. cross-group drag).
 */
export function SortableContainer({
  sensors: customSensors,
  collisionDetection = closestCenter,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDragCancel,
  renderOverlay,
  children,
}: SortableContainerProps) {
  const defaultSensors = useDefaultSensors();
  const sensors = customSensors ?? defaultSensors;
  const [active, setActive] = useState<Active | null>(null);

  function handleDragStart(event: DragStartEvent) {
    setActive(event.active);
    onDragStart?.(event);
  }

  function handleDragOver(event: DragOverEvent) {
    onDragOver?.(event);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActive(null);
    onDragEnd?.(event);
  }

  function handleDragCancel(event: DragCancelEvent) {
    setActive(null);
    onDragCancel?.(event);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collisionDetection}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      {children}
      <DragOverlay>
        {active && renderOverlay ? (
          <IsOverlayContext.Provider value={true}>
            {renderOverlay(active)}
          </IsOverlayContext.Provider>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export interface SortableSubListProps<T extends { id: number | string }> {
  items: (T | number | string)[];
  strategy?: SortingStrategy;
  children: ReactNode;
  as?: "ul" | "ol" | "div";
  className?: string;
  style?: CSSProperties;
  id?: string;
}

/**
 * Pure SortableContext wrapper without its own DndContext.
 * Must be used inside a SortableContainer.
 */
export function SortableSubList<T extends { id: number | string }>({
  items,
  strategy = verticalListSortingStrategy,
  children,
  as: Component = "div",
  className,
  style,
  id,
}: SortableSubListProps<T>) {
  const itemIds = useMemo(
    () =>
      items.map((item) =>
        typeof item === "object" && item !== null && "id" in item
          ? item.id
          : item,
      ),
    [items],
  );

  return (
    <SortableContext id={id} items={itemIds} strategy={strategy}>
      <Component className={className} style={style}>
        {children}
      </Component>
    </SortableContext>
  );
}

export interface SortableListProps<T extends { id: number | string }> {
  items: T[];
  onReorder: (activeId: T["id"], newIndex: number) => void | Promise<void>;
  strategy?: SortingStrategy;
  children: ReactNode;
  as?: "ul" | "ol" | "div";
  className?: string;
  style?: CSSProperties;
  renderOverlay?: (activeItem: T) => ReactNode;
}

/**
 * Self-contained sortable list with its own DndContext and DragOverlay.
 * Preserves zero-change compatibility for existing single-list callers (Todo, Evidence Case/Block).
 */
export function SortableList<T extends { id: number | string }>({
  items,
  onReorder,
  strategy = verticalListSortingStrategy,
  children,
  as = "div",
  className,
  style,
  renderOverlay,
}: SortableListProps<T>) {
  const [activeItem, setActiveItem] = useState<T | null>(null);

  function handleDragStart(event: DragStartEvent) {
    const found =
      items.find((item) => String(item.id) === String(event.active.id)) ?? null;
    setActiveItem(found);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveItem(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex(
      (item) => String(item.id) === String(active.id),
    );
    const newIndex = items.findIndex(
      (item) => String(item.id) === String(over.id),
    );

    if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
      void onReorder(active.id as T["id"], newIndex);
    }
  }

  function handleDragCancel() {
    setActiveItem(null);
  }

  const activeChild = useMemo(() => {
    if (!activeItem) return null;
    const childList = React.Children.toArray(children);
    return (
      childList.find((child) => {
        if (!React.isValidElement(child)) return false;
        const key = child.key?.toString().replace(/^\.\$/, "");
        return key === String(activeItem.id);
      }) ?? null
    );
  }, [children, activeItem]);

  return (
    <SortableContainer
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
      renderOverlay={() => {
        if (renderOverlay && activeItem) {
          return renderOverlay(activeItem);
        }
        if (activeChild) {
          return (
            <div className="shadow-xl rounded-md pointer-events-none opacity-95">
              {activeChild}
            </div>
          );
        }
        return null;
      }}
    >
      <SortableSubList
        items={items}
        strategy={strategy}
        as={as}
        className={className}
        style={style}
      >
        {children}
      </SortableSubList>
    </SortableContainer>
  );
}

export function useSortableItem(
  id: number | string,
  disabled?: boolean,
  data?: Record<string, unknown>,
) {
  const isOverlay = useContext(IsOverlayContext);
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled: disabled || isOverlay, data });

  if (isOverlay) {
    return {
      ref: undefined,
      style: {
        pointerEvents: "none" as const,
        opacity: 1,
      },
      isDragging: false,
      handleProps: {
        ref: undefined,
      },
    };
  }

  const style: CSSProperties = {
    transform: isDragging ? undefined : CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : undefined,
    zIndex: isDragging ? 0 : undefined,
    position: "relative",
  };

  const handleProps = {
    ...attributes,
    ...listeners,
    ref: setActivatorNodeRef,
  };

  return {
    ref: setNodeRef,
    style,
    isDragging,
    handleProps,
  };
}

export interface DragHandleProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  title?: string;
  size?: number;
}

export function DragHandle({
  className,
  title,
  size = 12,
  ...props
}: DragHandleProps) {
  return (
    <button
      type="button"
      className={className ?? "tool-btn cursor-grab active:cursor-grabbing"}
      title={title}
      {...props}
    >
      <DragHandleIcon size={size} />
    </button>
  );
}
