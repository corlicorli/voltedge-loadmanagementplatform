import type { ReactNode } from "react";

import { CardHeader, CardTitle } from "@/components/ui/card";

/** Section heading used across cards: a tinted icon chip + a normal-case title,
    with an optional element on the right. */
export function CardHeading({
  icon,
  color,
  title,
  right,
}: {
  icon: ReactNode;
  color: string;
  title: string;
  right?: ReactNode;
}) {
  return (
    <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
      <CardTitle className="flex items-center gap-2.5 text-[15px] font-semibold">
        <span
          className="grid h-8 w-8 place-items-center rounded-lg"
          style={{ backgroundColor: color.replace(")", " / 0.12)"), color }}
        >
          {icon}
        </span>
        {title}
      </CardTitle>
      {right}
    </CardHeader>
  );
}
