import { cn } from "@/utils/cn";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-shimmer bg-linear-to-r from-slate-100 via-slate-200/70 to-slate-100 bg-[length:200%_100%] rounded-md",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
