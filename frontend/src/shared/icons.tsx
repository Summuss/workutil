import type { SVGProps } from "react";

/**
 * The small stroke-icon set used throughout the app, matching the design
 * mockup's icon language (feather-style, 2px stroke, rounded caps/joins).
 * Kept as one module so every feature draws from the same visual vocabulary
 * instead of pasting SVG markup per component.
 */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base(size: number, props: IconProps) {
  const { size: _size, ...rest } = props;
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    ...rest,
  };
}

export function SearchIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 14, props)}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.2" y2="16.2" />
    </svg>
  );
}

export function EditIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

export function ChevronUpIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function ChevronLeftIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export function ChevronsUpIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="17 11 12 6 7 11" />
      <polyline points="17 18 12 13 7 18" />
    </svg>
  );
}

export function ChevronsDownIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="7 13 12 18 17 13" />
      <polyline points="7 6 12 11 17 6" />
    </svg>
  );
}

export function ChevronsLeftIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="13 17 8 12 13 7" />
      <polyline points="20 17 15 12 20 7" />
    </svg>
  );
}

export function ChevronsRightIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <polyline points="4 17 9 12 4 7" />
      <polyline points="11 17 16 12 11 7" />
    </svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 12, props)} strokeWidth={2.3}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)} strokeWidth={2.5}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export function XIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 12, props)} strokeWidth={2.3}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 11, props)} strokeWidth={2.5}>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 14, props)}>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

export function ImageIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 22, props)} strokeWidth={1.6}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  );
}

export function FolderIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 14, props)}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
    </svg>
  );
}

export function ExternalLinkIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 12, props)}>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

export function DragHandleIcon(props: IconProps) {
  return (
    <svg {...base(props.size ?? 13, props)}>
      <circle cx="9" cy="6" r="1" fill="currentColor" stroke="currentColor" />
      <circle cx="9" cy="12" r="1" fill="currentColor" stroke="currentColor" />
      <circle cx="9" cy="18" r="1" fill="currentColor" stroke="currentColor" />
      <circle cx="15" cy="6" r="1" fill="currentColor" stroke="currentColor" />
      <circle cx="15" cy="12" r="1" fill="currentColor" stroke="currentColor" />
      <circle cx="15" cy="18" r="1" fill="currentColor" stroke="currentColor" />
    </svg>
  );
}

