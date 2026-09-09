import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  sortableKeyboardCoordinates,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  type SortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useMemo,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type ReactNode,
} from "react";

import { DragHandleIcon } from "../icons";

export interface SortableListProps<T extends { id: number | string }> {
  items: T[];
  onReorder: (activeId: T["id"], newIndex: number) => void | Promise<void>;
  strategy?: SortingStrategy;
  children: ReactNode;
  as?: "ul" | "ol" | "div";
  className?: string;
  style?: CSSProperties;
}

export function SortableList<T extends { id: number | string }>({
  items,
  onReorder,
  strategy = verticalListSortingStrategy,
  children,
  as: Component = "div",
  className,
  style,
}: SortableListProps<T>) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 3,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const itemIds = useMemo(() => items.map((item) => item.id), [items]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex((item) => item.id === active.id);
    const newIndex = items.findIndex((item) => item.id === over.id);

    if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
      void onReorder(active.id as T["id"], newIndex);
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={itemIds} strategy={strategy}>
        <Component className={className} style={style}>
          {children}
        </Component>
      </SortableContext>
    </DndContext>
  );
}

export function useSortableItem(id: number | string, disabled?: boolean) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled });

  const style: CSSProperties = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : undefined,
    zIndex: isDragging ? 20 : undefined,
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
