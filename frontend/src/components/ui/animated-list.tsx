"use client";

import React, { ReactElement, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/utils/cn";

export interface AnimatedListProps {
  className?: string;
  children: React.ReactNode;
  delay?: number;
}

export const AnimatedList = React.memo(
  ({ className, children, delay = 1000 }: AnimatedListProps) => {
    const childrenArray = React.Children.toArray(children);
    const [index, setIndex] = useState(0);

    useEffect(() => {
      if (index < childrenArray.length - 1) {
        const timeout = setTimeout(() => {
          setIndex((prevIndex) => prevIndex + 1);
        }, delay);
        return () => clearTimeout(timeout);
      }
    }, [index, delay, childrenArray.length]);

    const itemsToShow = childrenArray.slice(0, index + 1).reverse();

    return (
      <div className={cn("flex flex-col items-center gap-3 w-full", className)}>
        <AnimatePresence>
          {itemsToShow.map((item) => (
            <AnimatedListItem key={(item as ReactElement).key || Math.random()}>
              {item}
            </AnimatedListItem>
          ))}
        </AnimatePresence>
      </div>
    );
  }
);

AnimatedList.displayName = "AnimatedList";

export function AnimatedListItem({ children }: { children: React.ReactNode }) {
  const animations = {
    initial: { scale: 0.95, opacity: 0, y: 12 },
    animate: { scale: 1, opacity: 1, y: 0 },
    exit: { scale: 0.95, opacity: 0, y: -12 },
    transition: { type: "spring" as const, stiffness: 350, damping: 25 },
  };

  return (
    <motion.div {...animations} className="mx-auto w-full">
      {children}
    </motion.div>
  );
}
