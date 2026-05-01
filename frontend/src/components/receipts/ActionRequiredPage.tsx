import { useNavigate } from "@tanstack/react-router";
import { ArrowLeft, ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { UserReceipts } from "@/types";
import { useMemo, useState, useCallback, useEffect } from "react";
import { ReceiptEditModal } from "./ReceiptEditModal";
import { Card, CardContent } from "@/components/ui/card";
import { formattedRupiah } from "@/utils/currency";
import { useQuery } from "@tanstack/react-query";
import { getToken } from "@/lib/auth";
import type { UserData } from "@/types";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

export const ActionRequiredPage = () => {
  const navigate = useNavigate();
  // const [receipts, setReceipts] = useState<UserReceipts[]>(() => {
  //   const saved = localStorage.getItem("mock_receipts");
  //   return saved ? JSON.parse(saved) : [];
  // });
  const [selectedReceipt, setSelectedReceipt] = useState<UserReceipts | null>(
    null,
  );
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Sync with localStorage
  // useEffect(() => {
  //   localStorage.setItem("mock_receipts", JSON.stringify(receipts));
  // }, [receipts]);

  const { data, refetch } = useQuery<UserData>({
    queryKey: ["userReceipts"], // ← queryKey sama biar shared cache
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Unauthenticated");

      const res = await fetch(`${BACKEND_URL}/api/receipts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    staleTime: 30 * 1000,
  });

  useEffect(() => {
    console.log("action req page", data);
  }, [data]);

  const actionRequiredReceipts = useMemo(
    () => (data?.receipts ?? []).filter((r) => r.status === "ACTION_REQUIRED"),
    [data],
  );

  const handleReviewReceipt = useCallback((receipt: UserReceipts) => {
    setSelectedReceipt(receipt);
    setIsEditModalOpen(true);
  }, []);

  const handleSaveReceipt = useCallback(async () => {
    await refetch(); // ← refetch aja, gak perlu update local state
  }, [refetch]);

  // const actionRequiredReceipts = useMemo(
  //   () => receipts.filter((r) => r.status === "ACTION_REQUIRED"),
  //   [receipts],
  // );

  const handleBack = () => {
    navigate({ to: "/receipts" });
  };

  // const handleReviewReceipt = useCallback((receipt: UserReceipts) => {
  //   setSelectedReceipt(receipt);
  //   setIsEditModalOpen(true);
  // }, []);

  // const handleSaveReceipt = useCallback((updatedReceipt: UserReceipts) => {
  //   setReceipts((prev) =>
  //     prev.map((r) => (r.id === updatedReceipt.id ? updatedReceipt : r)),
  //   );
  // }, []);

  return (
    <div className="pb-24 min-h-screen bg-[#0b0e11] text-white">
      {/* Header */}
      <div className="py-6 px-4 flex items-center gap-4 sticky top-0 bg-[#0b0e11]/80 backdrop-blur-md z-10 border-b border-gray-800/50">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleBack}
          className="text-white hover:bg-white/10 p-0 h-10 w-10 shrink-0"
        >
          <ArrowLeft className="h-6 w-6" />
        </Button>
        <h1 className="text-xl font-black bg-linear-to-r from-white to-gray-400 bg-clip-text text-transparent">
          Action Required
        </h1>
      </div>

      <div className="p-4">
        <p className="text-gray-500 font-bold text-sm mb-6 px-1">
          {actionRequiredReceipts.length} RECEIPTS REQUIRE YOUR REVIEW
        </p>

        <div className="space-y-4">
          {actionRequiredReceipts.map((receipt) => (
            <ActionRequiredListItem
              key={receipt.id}
              receipt={receipt}
              onReview={() => handleReviewReceipt(receipt)}
            />
          ))}
        </div>
      </div>

      {/* Edit Modal */}
      {selectedReceipt && (
        <ReceiptEditModal
          receipt={selectedReceipt}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSaveReceipt}
        />
      )}
    </div>
  );
};

interface ActionRequiredListItemProps {
  receipt: UserReceipts;
  onReview: () => void;
}

const ActionRequiredListItem = ({
  receipt,
  onReview,
}: ActionRequiredListItemProps) => {
  const date = new Date(receipt.receipt_items[0]?.created_at || receipt.transaction_date);
  const dateLabel = "Today"; // Simple for mock
  const timeLabel = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  });

  const avgConfidence =
    receipt.low_confidence_fields?.length > 0
      ? receipt.low_confidence_fields.reduce(
          (acc, f) => acc + f.confidence,
          0,
        ) / receipt.low_confidence_fields.length
      : 0.65;

  return (
    <Card className="bg-[#1a2129] border border-gray-800/50 rounded-[24px] text-white overflow-hidden shadow-xl">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-12 w-12 bg-[#252a31] rounded-xl flex items-center justify-center shrink-0">
              <ShoppingBag className="h-6 w-6 text-gray-400" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-base truncate">
                {receipt.store_name}
              </p>
              <p className="text-xs text-gray-400">
                {dateLabel} • {timeLabel}
              </p>
            </div>
          </div>
          <Button
            onClick={onReview}
            variant="ghost"
            className="text-blue-500 hover:text-blue-400 hover:bg-blue-500/10 font-bold p-0 h-auto"
          >
            Verify Now
          </Button>
        </div>

        <div className="flex items-baseline gap-1 mb-5">
          <span className="text-2xl font-black text-white">
            {formattedRupiah(receipt.total_amount)}
          </span>
          <span className="text-sm text-gray-500 font-medium">(Est)</span>
        </div>

        <div className="space-y-2">
          <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-yellow-500 rounded-full"
              style={{ width: `${avgConfidence * 100}%` }}
            />
          </div>
          <div className="flex justify-end">
            <span className="text-xs font-bold text-yellow-500">
              Confirm Total
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
