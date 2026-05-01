import { useMemo, useState } from "react";
import type { UserReceipts } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formattedRupiah } from "@/utils/currency";
import {
  ShoppingBag,
  Coffee,
  Monitor,
  ShoppingCart,
  Store,
  CheckCircle2,
  Clock,
} from "lucide-react";

interface RecentActivityListProps {
  receipts: UserReceipts[];
  onReceiptClick?: (receipt: UserReceipts) => void;
  onStatusClick?: (receipt: UserReceipts, status: string) => void;
}

const storeIcons: Record<string, { icon: typeof ShoppingBag; color: string }> =
  {
    default: { icon: Store, color: "bg-gray-600" },
  };

const iconPool = [
  { icon: ShoppingBag, color: "bg-red-500/80" },
  { icon: Coffee, color: "bg-amber-600/80" },
  { icon: Monitor, color: "bg-blue-500/80" },
  { icon: ShoppingCart, color: "bg-green-500/80" },
];

function getStoreIcon(storeName: string) {
  if (storeIcons[storeName]) return storeIcons[storeName];
  const hash = storeName
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const entry = iconPool[hash % iconPool.length];
  storeIcons[storeName] = entry;
  return entry;
}

const statusConfig: Record<
  string,
  { label: string; className: string; icon?: any }
> = {
  VERIFIED: {
    label: "VERIFIED",
    className: "bg-green-500/20 text-green-400 border-green-500/30",
    icon: CheckCircle2,
  },
  PENDING: {
    label: "PENDING",
    className: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    icon: Clock,
  },
  ACTION_REQUIRED: {
    label: "ACTION REQUIRED",
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
};

export const RecentActivityList = ({
  receipts,
  onReceiptClick,
  onStatusClick,
}: RecentActivityListProps) => {
  const [tooltip, setTooltip] = useState<{ id: string; text: string } | null>(
    null,
  );

  const groupedReceipts = useMemo(() => {
    const groups: Record<string, UserReceipts[]> = {};
    const now = new Date();
    const today = now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const yesterdayStr = yesterday.toDateString();
    const thisMonth = now.getMonth();
    const thisYear = now.getFullYear();

    receipts.forEach((receipt) => {
      const date = new Date(
        receipt.receipt_items[0]?.created_at || receipt.transaction_date,
      );
      const dateStr = date.toDateString();
      let groupKey = "";

      if (dateStr === today) {
        groupKey = "TODAY";
      } else if (dateStr === yesterdayStr) {
        groupKey = "YESTERDAY";
      } else if (
        date.getMonth() === thisMonth &&
        date.getFullYear() === thisYear
      ) {
        groupKey = "THIS MONTH";
      } else {
        groupKey = date
          .toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })
          .toUpperCase();
      }

      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(receipt);
    });

    return groups;
  }, [receipts]);

  const handleStatusClick = (e: React.MouseEvent, receipt: UserReceipts) => {
    e.stopPropagation();
    const status = receipt.status || "VERIFIED";

    if (status === "PENDING") {
      setTooltip({ id: receipt.id, text: "Processing..." });
      setTimeout(() => setTooltip(null), 2000);
    } else {
      onStatusClick?.(receipt, status);
    }
  };

  if (receipts.length === 0) return null;

  return (
    <div className="px-4 pb-4">
      <h2 className="text-lg font-bold text-white mb-6">Recent Activity</h2>
      <div className="space-y-8">
        {Object.entries(groupedReceipts).map(([group, items]) => (
          <div key={group} className="relative">
            <div className="sticky top-0 z-10 bg-[#0b0e11]/80 backdrop-blur-md py-2 mb-2">
              <h3 className="text-xs font-bold text-gray-500 tracking-wider">
                {group}
              </h3>
            </div>
            <div className="space-y-3">
              {items.map((receipt) => {
                const date = new Date(receipt.receipt_items[0] && receipt.transaction_date);
                const timeLabel = date.toLocaleTimeString("en-US", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  hour: "numeric",
                  minute: "numeric",
                  hour12: false,
                });

                const status = receipt.status || "VERIFIED";
                const statusInfo =
                  statusConfig[status] || statusConfig.verified;
                const { icon: StoreIcon, color } = getStoreIcon(
                  receipt.store_name,
                );
                const StatusIcon = statusInfo.icon;

                return (
                  <Card
                    key={receipt.id}
                    className="bg-[#1a2129] border-none rounded-2xl text-white cursor-pointer hover:bg-[#1e2730] transition-colors relative"
                    onClick={() => onReceiptClick?.(receipt)}
                  >
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`h-12 w-12 ${color} rounded-2xl flex items-center justify-center shrink-0 shadow-lg`}
                        >
                          <StoreIcon className="h-6 w-6 text-white" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold truncate text-[15px]">
                            {receipt.store_name}
                          </p>
                          <p className="text-xs text-gray-400 font-medium">
                            {timeLabel}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0 ml-3">
                        <p className="font-black text-base">
                          {formattedRupiah(receipt.total_amount)}
                        </p>
                        <div className="relative">
                          <Badge
                            variant="outline"
                            className={`text-[9px] font-bold px-2 py-0.5 mt-1.5 rounded-full flex items-center gap-1 border ${statusInfo.className}`}
                            onClick={(e) => handleStatusClick(e, receipt)}
                          >
                            {StatusIcon ? (
                              <StatusIcon className="h-2.5 w-2.5" />
                            ) : (
                              <span className="text-[10px]">●</span>
                            )}
                            {statusInfo.label}
                          </Badge>
                          {tooltip?.id === receipt.id && (
                            <div className="absolute bottom-full right-0 mb-2 px-2 py-1 bg-gray-800 text-white text-[10px] rounded shadow-lg animate-in fade-in slide-in-from-bottom-1">
                              {tooltip.text}
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
