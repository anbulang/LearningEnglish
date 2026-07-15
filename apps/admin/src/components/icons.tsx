/* Inline stroke icons shared across the console screens (currentColor-driven). */
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base({ size = 16, strokeWidth = 1.6, children, ...rest }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth as number}
      {...rest}
    >
      {children}
    </svg>
  );
}

export function IconSearch(props: IconProps) {
  return base({
    ...props,
    children: (
      <>
        <circle cx="7" cy="7" r="4.2" />
        <path d="M10.2 10.2L13.5 13.5" strokeLinecap="round" />
      </>
    )
  });
}

export function IconX(props: IconProps) {
  return base({
    strokeWidth: 1.7,
    ...props,
    children: <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
  });
}

export function IconTrash(props: IconProps) {
  return base({
    ...props,
    children: <path d="M3 4.5h10M6.5 4.5V3h3v1.5M5 4.5l.6 8.5h4.8L11 4.5" strokeLinecap="round" strokeLinejoin="round" />
  });
}

export function IconChevronRight(props: IconProps) {
  return base({
    strokeWidth: 1.5,
    ...props,
    children: <path d="M6 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
  });
}

export function IconCheck(props: IconProps) {
  return base({
    strokeWidth: 2,
    ...props,
    children: <path d="M3.2 8.4l3 3 6.6-7" strokeLinecap="round" strokeLinejoin="round" />
  });
}

export function IconShield(props: IconProps) {
  return (
    <svg
      width={props.size ?? 22}
      height={props.size ?? 22}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      {...props}
    >
      <path d="M12 3l8 3v5c0 4.5-3 7.7-8 9-5-1.3-8-4.5-8-9V6z" strokeLinejoin="round" />
      <path d="M12 8.5v4M12 15.5h.01" strokeLinecap="round" />
    </svg>
  );
}

export function IconInfo(props: IconProps) {
  return (
    <svg
      width={props.size ?? 17}
      height={props.size ?? 17}
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      {...props}
    >
      <circle cx="9" cy="9" r="7" />
      <path d="M9 8v4M9 5.6h.01" strokeLinecap="round" />
    </svg>
  );
}
