import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/utils/cn";

const alertVariants = cva(
  "relative w-full rounded-md border p-4 [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-slate-950 [&>svg+div]:translate-y-[-3px] [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-slate-50 border-slate-200 text-slate-800 [&>svg]:text-slate-600",
        info: "bg-sky-50 border-sky-200 text-sky-900 [&>svg]:text-sky-600",
        success: "bg-emerald-50 border-emerald-200 text-emerald-900 [&>svg]:text-emerald-600",
        warning: "bg-amber-50 border-amber-200 text-amber-900 [&>svg]:text-amber-600",
        danger: "bg-rose-50 border-rose-200 text-rose-900 [&>svg]:text-rose-600",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

const iconMap = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
};

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string;
  hideIcon?: boolean;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", title, hideIcon = false, children, ...props }, ref) => {
    const IconComponent = iconMap[variant || "default"];

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        {!hideIcon && <IconComponent className="h-4 w-4" />}
        <div>
          {title && <h5 className="mb-1 text-sm font-semibold leading-none tracking-tight">{title}</h5>}
          <div className="text-xs leading-relaxed opacity-90">{children}</div>
        </div>
      </div>
    );
  }
);
Alert.displayName = "Alert";

export { Alert };
