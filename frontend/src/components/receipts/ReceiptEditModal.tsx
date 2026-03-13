import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { UserReceipts, ReceiptItem } from "@/types";
import {
  calculateTotal,
  calculateReceiptSummary,
} from "@/utils/calculateDicountVoucher";
import { getToken } from "@/lib/auth";
import {
  X,
  // ZoomIn,
  // ZoomOut,
  Calendar,
  Clock,
  AlertTriangle,
  Plus,
  Trash2,
  Maximize2,
  CheckCircle2,
  // Info,
  // ChevronUp,
  MoreVertical,
  ShoppingBag,
  GitMerge,
} from "lucide-react";
import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formattedRupiah } from "@/utils/currency"; // Assuming we have this or similar currency formatter

// Custom Input with dark theme styling to match design
const DarkInput = ({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input
    className={`bg-[#0f1419] border border-gray-800 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:border-blue-500 transition-colors ${className}`}
    {...props}
  />
);

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

interface ReceiptEditModalProps {
  receipt: UserReceipts;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
  isReadOnly?: boolean;
}

export const ReceiptEditModal = ({
  receipt,
  isOpen,
  onClose,
  onSave,
  isReadOnly = false,
}: ReceiptEditModalProps) => {
  const [editedReceipt, setEditedReceipt] = useState<UserReceipts>(receipt);
  // const [zoomLevel, setZoomLevel] = useState(1);
  // const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  // const [isDragging, setIsDragging] = useState(false);
  // const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // const [isDeleting, setIsDeleting] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      const res = await fetch(
        `${BACKEND_URL}/api/receipts/${editedReceipt.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      toast.success("Receipt deleted successfully");
      queryClient.invalidateQueries({ queryKey: ["userReceipts"] });
      onSave(); // trigger refetch di parent
      onClose();
      setIsDeleteConfirmOpen(false);
      navigate({ to: "/receipts" });
    },
    onError: (err) => {
      console.error(err);
      toast.error("Failed to delete receipt");
    },
  });

  // const [showFullImage, setShowFullImage] = useState(false);

  // State is now initialized once on mount
  // Parent uses key={receipt.id} to handle receipt changes

  if (!isOpen) return null;

  // const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.5, 3));
  // const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.5, 1));

  const summary = calculateReceiptSummary(editedReceipt.receipt_items);
  const itemsTotal = summary.total;

  const totalMismatch = Math.abs(itemsTotal - editedReceipt.total_amount) > 100; // Allow small rounding diff

  // const handleSave = () => {
  //   // If it was action-required, it moves to pending.
  //   // If it was pending (already processing), we might want to manually 'verify' it for testing.
  //   const nextStatus =
  //     editedReceipt.status === "ACTION_REQUIRED" ? "PENDING" : "VERIFIED";

  //   // Track what was edited
  //   const editedFields: string[] = [...(editedReceipt.edited_fields || [])];

  //   if (
  //     editedReceipt.store_name !== receipt.store_name &&
  //     !editedFields.includes("store_name")
  //   ) {
  //     editedFields.push("store_name");
  //   }
  //   if (
  //     editedReceipt.total_amount !== receipt.total_amount &&
  //     !editedFields.includes("total_amount")
  //   ) {
  //     editedFields.push("total_amount");
  //   }
  //   if (
  //     editedReceipt.transaction_date !== receipt.transaction_date &&
  //     !editedFields.includes("transaction_date")
  //   ) {
  //     editedFields.push("transaction_date");
  //   }
  //   if (
  //     JSON.stringify(editedReceipt.receipt_items) !==
  //       JSON.stringify(receipt.receipt_items) &&
  //     !editedFields.includes("items")
  //   ) {
  //     editedFields.push("items");
  //   }

  //   onSave({
  //     ...editedReceipt,
  //     status: nextStatus,
  //     edited_fields: editedFields,
  //   });
  //   onClose();
  // };

  const handleSave = () => {
    setIsConfirmModalOpen(true);
  };

  const confirmSave = async () => {
    setIsSaving(true);
    const nextStatus =
      editedReceipt.status === "ACTION_REQUIRED" ? "VERIFIED" : "VERIFIED";
    const token = await getToken();

    const editedFields: string[] = [];
    if (editedReceipt.store_name !== receipt.store_name)
      editedFields.push("store_name");
    if (editedReceipt.total_amount !== receipt.total_amount)
      editedFields.push("total_amount");
    if (editedReceipt.transaction_date !== receipt.transaction_date)
      editedFields.push("transaction_date");
    if (
      JSON.stringify(editedReceipt.receipt_items) !==
      JSON.stringify(receipt.receipt_items)
    )
      editedFields.push("items");

    try {
      // Hit BE buat update receipt
      const res = await fetch(
        `${BACKEND_URL}/api/receipts/${editedReceipt.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            ...editedReceipt,
            status: nextStatus,
            edited_fields: editedFields,
          }),
        },
      );

      if (!res.ok) throw new Error(`Error: ${res.status}`);

      toast.success("Receipt updated successfully");
      onSave(); // trigger refetch di parent
      onClose();
      setIsConfirmModalOpen(false);

      // Redirect back to receipts page
      navigate({ to: "/receipts" });
    } catch (err) {
      console.error(err);
      toast.error("Failed to update receipt");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddItem = () => {
    const newItem: ReceiptItem = {
      id: Math.random().toString(36).substr(2, 9),
      name: "",
      qty: 1,
      price: 0,
      total_price: 0,
      category: "Uncategorized",
      created_at: new Date().toISOString(),
    };
    setEditedReceipt({
      ...editedReceipt,
      receipt_items: [...editedReceipt.receipt_items, newItem],
    });
  };

  const handleDeleteItem = (id: string) => {
    setEditedReceipt({
      ...editedReceipt,
      receipt_items: editedReceipt.receipt_items.filter(
        (item) => item.id !== id,
      ),
    });
  };

  const updateItem = (idx: number, updates: Partial<ReceiptItem>) => {
    const newItems = [...editedReceipt.receipt_items];
    const updated = { ...newItems[idx], ...updates };

    // Auto-recalculate total_price
    updated.total_price = calculateTotal(updated);

    newItems[idx] = updated;
    setEditedReceipt({ ...editedReceipt, receipt_items: newItems });
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background animate-in slide-in-from-bottom-full duration-300">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-[#0f1419] border-b border-gray-800 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="text-gray-400 hover:text-white"
        >
          <X className="h-6 w-6" />
        </Button>
        <span className="text-lg font-semibold text-white">
          {isReadOnly ? "Receipt Details" : "Verify Receipt"}
        </span>
        <div className="flex gap-2 relative">
          {isReadOnly && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="text-gray-400 hover:text-white"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
              >
                <MoreVertical className="h-5 w-5" />
              </Button>

              {isMenuOpen && (
                <div className="absolute right-0 top-12 w-48 bg-[#1a2129] border border-gray-800 rounded-xl shadow-2xl z-20 py-1 animate-in fade-in zoom-in-95 duration-100">
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      setIsDeleteConfirmOpen(true);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-3 text-red-500 hover:bg-red-500/10 transition-colors text-sm font-medium"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete Receipt
                  </button>
                </div>
              )}
            </>
          )}
          {!isReadOnly && <div className="w-10" />}
        </div>
      </div>

      {/* Main Content - Split or Scrollable */}
      <div className="flex-1 overflow-y-auto bg-[#0b0e11] relative">
        {/* Image Section — only shown for action-required (editing mode) */}
        {/* {!isReadOnly && (
          <div className="h-75 bg-[#1a2129] relative overflow-hidden group shrink-0">

            <div
              className="w-full h-full flex items-center justify-center cursor-move"
              style={{
                transform: `scale(${zoomLevel}) translate(${panPosition.x}px, ${panPosition.y}px)`,
                transition: isDragging ? "none" : "transform 0.2s ease-out",
              }}
              onMouseDown={(e) => {
                setIsDragging(true);
                setDragStart({
                  x: e.clientX - panPosition.x,
                  y: e.clientY - panPosition.y,
                });
              }}
              onMouseMove={(e) => {
                if (isDragging) {
                  setPanPosition({
                    x: e.clientX - dragStart.x,
                    y: e.clientY - dragStart.y,
                  });
                }
              }}
              onMouseUp={() => setIsDragging(false)}
              onMouseLeave={() => setIsDragging(false)}
            >
              <img
                src="https://images.unsplash.com/photo-1596558450268-9c27524ba856?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
                alt="Receipt"
                className="max-w-none w-auto h-auto min-w-50 object-contain opacity-80"
              />

              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 border-2 border-yellow-500 bg-yellow-500/10 w-48 h-24 rounded pointer-events-none" />
            </div> */}

            {/* Image Controls */}
            {/* <div className="absolute bottom-4 right-4 flex flex-col gap-2">
              <Button
                size="icon"
                variant="secondary"
                className="bg-gray-800 text-white rounded-full h-10 w-10"
                onClick={handleZoomIn}
              >
                <Plus className="h-5 w-5" />
              </Button>
              <Button
                size="icon"
                variant="secondary"
                className="bg-gray-800 text-white rounded-full h-10 w-10"
                onClick={handleZoomOut}
              >
                <div className="h-0.5 w-4 bg-white" />
              </Button>
            </div> */}

            {/* <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">

            </div> */}
          {/* </div> */}
        {/* )} */}

        {/* Drag Handle for Bottom Sheet look */}
        <div
          className={`bg-[#0f1419] relative px-6 pb-24 ${!isReadOnly ? "rounded-t-3xl -mt-6 pt-2 shadow-[0_-4px_20px_rgba(0,0,0,0.5)]" : "pt-6"}`}
        >
          {!isReadOnly && (
            <div className="w-12 h-1.5 bg-gray-700 rounded-full mx-auto mb-6" />
          )}

          {/* Section: Details */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <div className="bg-blue-600/20 p-1.5 rounded-lg">
                <ReceiptIcon className="h-5 w-5 text-blue-500" />
              </div>
              <h3 className="text-lg font-bold text-white">Details</h3>
            </div>

            <div className="space-y-4">
              {/* Store Name & Status Badge */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`h-12 w-12 rounded-xl flex items-center justify-center shrink-0 ${
                      receipt.status === "VERIFIED"
                        ? "bg-red-500/10"
                        : "bg-blue-600/20"
                    }`}
                  >
                    {receipt.status === "VERIFIED" ? (
                      <ShoppingBag className="h-6 w-6 text-red-500" />
                    ) : (
                      <ReceiptIcon className="h-6 w-6 text-blue-500" />
                    )}
                  </div>
                  <div>
                    {isReadOnly ? (
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold text-white leading-tight">
                            {receipt.store_name}
                          </h2>
                          {receipt.status === "PENDING" &&
                            receipt.edited_fields?.includes("store_name") && (
                              <span className="text-[10px] text-blue-400 font-bold bg-blue-500/10 px-1.5 py-0.5 rounded leading-none border border-blue-500/20">
                                EDITED
                              </span>
                            )}
                        </div>
                      </div>
                    ) : (
                      <>
                        <label className="text-gray-400 text-sm mb-1.5 block">
                          Store Name
                        </label>
                        <DarkInput
                          value={editedReceipt.store_name}
                          onChange={(e) =>
                            setEditedReceipt({
                              ...editedReceipt,
                              store_name: e.target.value,
                            })
                          }
                          className="pr-10 border-yellow-600/50"
                        />
                      </>
                    )}
                    <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                      <span>
                        {new Date(receipt.transaction_date).toLocaleDateString(
                          "en-US",
                          { month: "short", day: "numeric", year: "numeric" },
                        )}{" "}
                        •{" "}
                        {new Date(receipt.transaction_date).toLocaleTimeString(
                          [],
                          { hour: "2-digit", minute: "2-digit" },
                        )}
                      </span>
                      {receipt.status === "PENDING" &&
                        receipt.edited_fields?.includes("transaction_date") && (
                          <span className="text-[9px] text-blue-400 font-bold">
                            (Edited)
                          </span>
                        )}
                    </div>
                  </div>
                </div>

                {isReadOnly && (
                  <Badge
                    className={`rounded-full py-0.5 px-2 text-[10px] flex items-center gap-1 border border-transparent ${
                      receipt.status === "VERIFIED"
                        ? "bg-green-500/20 text-green-400 border-green-500/30"
                        : "bg-orange-500/20 text-orange-400 border-orange-500/30"
                    }`}
                  >
                    {receipt.status === "VERIFIED" ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <Clock className="h-3 w-3" />
                    )}
                    {receipt.status.toUpperCase()}
                  </Badge>
                )}
              </div>

              {!isReadOnly && (
                <div className="flex items-center gap-1.5 mt-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />
                  <span className="text-xs text-yellow-500">
                    Low confidence score (65%)
                  </span>
                </div>
              )}

              {!isReadOnly ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    {/* Date */}
                    <div>
                      <label className="text-gray-400 text-sm mb-1.5 block">
                        Date
                      </label>
                      <div className="relative">
                        <DarkInput
                          value={new Date(
                            editedReceipt.transaction_date,
                          ).toLocaleDateString()}
                          onChange={() => {}}
                          className="pr-10"
                        />
                        <Calendar className="absolute right-3 top-2.5 h-4 w-4 text-gray-400" />
                      </div>
                    </div>

                    {/* Time */}
                    <div>
                      <label className="text-gray-400 text-sm mb-1.5 block">
                        Time
                      </label>
                      <div className="relative">
                        <DarkInput
                          value={new Date(
                            editedReceipt.transaction_date,
                          ).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                          onChange={() => {}}
                          className="pr-10"
                        />
                        <Clock className="absolute right-3 top-2.5 h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Total Amount */}
                    <div>
                      <label className="text-gray-400 text-sm mb-1.5 block">
                        Total Amount
                      </label>
                      <div className="relative">
                        <div className="absolute left-3 top-2.5 text-gray-400 font-semibold">
                          $
                        </div>
                        <DarkInput
                          value={editedReceipt.total_amount}
                          onChange={(e) =>
                            setEditedReceipt({
                              ...editedReceipt,
                              total_amount: Number(e.target.value),
                            })
                          }
                          className="pl-7 text-lg font-semibold bg-blue-900/10 border-blue-500/30 text-blue-100"
                        />
                        <Maximize2 className="absolute right-3 top-3 h-4 w-4 text-blue-500" />
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="pt-2">
                  {/* Total Amount card removed from here as it's now in the summary below items */}
                </div>
              )}
            </div>
          </div>

          <div className="h-px bg-gray-800 my-6" />

          {/* Section: Items */}
          <div>
            <div className="flex items-center justify-between mb-4 border-t border-dashed border-gray-800 pt-6">
              <div className="flex items-center gap-2">
                {!isReadOnly && (
                  <div className="bg-blue-600/20 p-1.5 rounded-lg">
                    <ListChecks className="h-5 w-5 text-blue-500" />
                  </div>
                )}
                <h3
                  className={`${isReadOnly ? "text-gray-400 text-sm font-medium" : "text-lg font-bold text-white"}`}
                >
                  Items
                </h3>
                {isReadOnly &&
                  receipt.status === "PENDING" &&
                  receipt.edited_fields?.includes("items") && (
                    <span className="text-[10px] text-blue-400 font-bold ml-2">
                      (Edited)
                    </span>
                  )}
              </div>
              {isReadOnly && receipt.status === "VERIFIED" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-blue-500 hover:text-blue-400 font-bold p-0 h-auto flex items-center gap-1.5"
                >
                  <GitMerge className="h-3.5 w-3.5" />
                  Split Bill
                </Button>
              )}
              {!isReadOnly && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-blue-400 hover:text-blue-300 gap-1 pr-0"
                  onClick={handleAddItem}
                >
                  <Plus className="h-4 w-4" /> Add Item
                </Button>
              )}
            </div>

            <div className="space-y-4">
              {editedReceipt.receipt_items.map((item, idx) => (
                <div
                  key={item.id}
                  className={`group relative ${isReadOnly ? "flex items-center justify-between" : ""}`}
                >
                  {isReadOnly ? (
                    <>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium">
                            {item.name}
                          </span>
                          {item.qty > 1 && (
                            <span className="text-[10px] text-gray-500 font-bold bg-gray-800/50 px-1.5 rounded">
                              x{item.qty}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-col gap-0.5">
                          {item.category && (
                            <span className="text-[10px] text-gray-500 italic">
                              {item.category}
                            </span>
                          )}
                          <div className="text-[10px] text-gray-400 flex items-center gap-1">
                            <span>
                              ({item.qty} x {formattedRupiah(item.price)})
                            </span>
                            {(item.discount_value ?? 0) > 0 && (
                              <>
                                <span className="text-red-400">
                                  -{" "}
                                  {item.discount_type === "percentage"
                                    ? `${item.discount_value}%`
                                    : formattedRupiah(item.discount_value ?? 0)}
                                </span>
                              </>
                            )}
                            {(item.voucher_amount ?? 0) > 0 && (
                              <>
                                <span className="text-purple-400">
                                  - {formattedRupiah(item.voucher_amount ?? 0)}{" "}
                                  (Voucher)
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <span className="text-white font-semibold">
                        {formattedRupiah(item.total_price)}
                      </span>
                    </>
                  ) : (
                    <>
                      <div className="flex items-end gap-2 mb-2">
                        <div className="flex-1">
                          <label className="text-[10px] text-gray-500 mb-1 block">
                            Item Name
                          </label>
                          <DarkInput
                            value={item.name}
                            onChange={(e) =>
                              updateItem(idx, { name: e.target.value })
                            }
                            className="text-sm h-9"
                          />
                        </div>
                        <div className="w-12">
                          <label className="text-[10px] text-gray-500 mb-1 block">
                            Qty
                          </label>
                          <DarkInput
                            type="number"
                            min="1"
                            value={item.qty}
                            onChange={(e) => {
                              const qty = Math.max(1, Number(e.target.value));
                              updateItem(idx, {
                                qty,
                              });
                            }}
                            className="text-sm h-9 px-2 text-center"
                          />
                        </div>
                        <div className="w-24">
                          <label className="text-[10px] text-gray-500 mb-1 block text-right">
                            Price
                          </label>
                          <div className="relative">
                            <span className="absolute left-2 top-2 text-gray-500 text-xs">
                              Rp
                            </span>
                            <DarkInput
                              type="number"
                              value={item.price}
                              onChange={(e) => {
                                const price = Number(e.target.value);
                                updateItem(idx, {
                                  price,
                                });
                              }}
                              className="text-right pl-4 text-sm h-9"
                            />
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteItem(item.id)}
                          className="text-gray-500 hover:text-red-500 mb-0.5 h-9 w-9"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mb-4">
                        <div>
                          <label className="text-[10px] text-gray-500 mb-1 block">
                            Disc. Type
                          </label>
                          <select
                            value={item.discount_type || ""}
                            onChange={(e) =>
                              updateItem(idx, {
                                discount_type: (e.target.value as any) || null,
                              })
                            }
                            className="bg-[#0f1419] border border-gray-800 rounded-lg px-2 py-1.5 text-white text-xs w-full focus:outline-none focus:border-blue-500 transition-colors"
                          >
                            <option value="">None</option>
                            <option value="percentage">Percentage (%)</option>
                            <option value="nominal">Nominal (Rp)</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-500 mb-1 block">
                            Disc. Value
                          </label>
                          <DarkInput
                            type="number"
                            value={item.discount_value || 0}
                            onChange={(e) =>
                              updateItem(idx, {
                                discount_value: Number(e.target.value),
                              })
                            }
                            className="text-xs h-8"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-500 mb-1 block">
                            Voucher
                          </label>
                          <DarkInput
                            type="number"
                            value={item.voucher_amount || 0}
                            onChange={(e) =>
                              updateItem(idx, {
                                voucher_amount: Number(e.target.value),
                              })
                            }
                            className="text-xs h-8"
                          />
                        </div>
                      </div>
                      <div className="w-full h-[0.5px] bg-gray-800/50 mb-2" />
                    </>
                  )}
                </div>
              ))}
            </div>

            {/* Receipt Summary Section */}
            <div className="mt-8 space-y-3 border-t border-dashed border-gray-800 pt-6 px-1">
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Subtotal</span>
                <span className="text-white font-medium">
                  {formattedRupiah(summary.subtotal)}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Total Diskon</span>
                <span className="text-red-400 font-medium">
                  -{formattedRupiah(summary.discount)}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">Total Voucher</span>
                <span className="text-purple-400 font-medium">
                  -{formattedRupiah(summary.voucher)}
                </span>
              </div>

              <div className="pt-4 border-t border-gray-800/50 mt-4">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold text-white uppercase tracking-tight">
                    Total
                  </span>
                  <div className="flex flex-col items-end">
                    <span className="text-xl font-black text-white">
                      {formattedRupiah(itemsTotal)}
                    </span>
                    {receipt.status === "PENDING" &&
                      receipt.edited_fields?.includes("total_amount") && (
                        <span className="text-[10px] text-blue-400 font-bold mt-0.5">
                          (Edited)
                        </span>
                      )}
                  </div>
                </div>
              </div>
            </div>

            {!isReadOnly && totalMismatch && (
              <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-between">
                <span className="text-gray-400 text-sm">Sum of items</span>
                <div className="flex items-center gap-2">
                  <span className="text-white font-semibold">
                    ${itemsTotal.toLocaleString()}
                  </span>
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                </div>
              </div>
            )}

            {!isReadOnly && totalMismatch && (
              <p className="text-xs text-red-400 mt-2 text-right">
                Sum of items does not match Receipt Total ($
                {editedReceipt.total_amount.toLocaleString()})
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 bg-[#0f1419] border-t border-gray-800 shrink-0 mb-4 space-y-3">
        {isReadOnly ? (
          <div className="w-full" />
        ) : (
          <>
            <Button
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl h-12 text-lg font-semibold"
              onClick={handleSave}
            >
              <CheckCircle2 className="mr-2 h-5 w-5" />
              Confirm & Save
            </Button>
            <div className="text-center pt-2">
              <button className="text-gray-500 text-sm flex items-center justify-center gap-2 mx-auto hover:text-gray-300 transition-colors">
                <AlertTriangle className="h-3 w-3" /> Report OCR Error
              </button>
            </div>
          </>
        )}
      </div>
      {/* Confirmation Modal Overlay */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#1a2129] border border-gray-800 rounded-3xl p-6 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-white mb-2">Save Changes?</h3>
            <p className="text-gray-400 mb-6">
              Are you sure you want to update this receipt? This will move it to{" "}
              <span className="text-green-400 font-semibold">Verified</span>{" "}
              status.
            </p>
            <div className="flex flex-col gap-3">
              <Button
                className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl h-12 font-bold"
                onClick={confirmSave}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Yes, Save Changes"}
              </Button>
              <Button
                variant="ghost"
                className="w-full text-gray-400 hover:text-white"
                onClick={() => setIsConfirmModalOpen(false)}
                disabled={isSaving}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Delete Confirmation Modal */}
      {isDeleteConfirmOpen && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#1a2129] border border-gray-800 rounded-3xl p-6 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="bg-red-500/10 h-16 w-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <Trash2 className="h-8 w-8 text-red-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2 text-center">
              Delete Receipt?
            </h3>
            <p className="text-gray-400 mb-6 text-center">
              This action cannot be undone. This receipt will be permanently
              removed.
            </p>
            <div className="flex flex-col gap-3">
              <Button
                className="w-full bg-red-600 hover:bg-red-700 text-white rounded-xl h-12 font-bold"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "Deleting..." : "Yes, Delete It"}
              </Button>
              <Button
                variant="ghost"
                className="w-full text-gray-400 hover:text-white font-medium"
                onClick={() => setIsDeleteConfirmOpen(false)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper components not imported
const ReceiptIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1Z" />
    <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" />
    <path d="M12 17V7" />
  </svg>
);

const ListChecks = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M10 6h11" />
    <path d="M10 12h11" />
    <path d="M10 18h11" />
    <path d="M4 6h1" />
    <path d="M4 12h1" />
    <path d="M4 18h1" />
  </svg>
);
