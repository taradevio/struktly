import { useState, useMemo, useCallback, useEffect } from "react";
// import type { Receipt } from "@/types";
import { ReceiptHeader } from "./ReceiptHeader";
import { ReceiptSearchBar } from "./ReceiptSearchBar";
import { ReceiptFilterChips, type FilterType } from "./ReceiptFilterChips";
import { ActionRequiredSection } from "./ActionRequiredSection";
import { RecentActivityList } from "./RecentActivityList";
import { ReceiptEmptyState } from "./ReceiptEmptyState";
import { ReceiptsSkeleton } from "./ReceiptsSkeleton";
import { ReceiptEditModal } from "./ReceiptEditModal";
import { usePullToRefresh } from "@/hooks/usePullToRefresh";
import { Loader2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { getToken } from "@/lib/auth";

const queryClient = new QueryClient();
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

import { type UserReceipts, type UserData } from "@/types";

export const ReceiptsPage = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Receipts />
    </QueryClientProvider>
  );
};

const Receipts = () => {
  const navigate = useNavigate();
  // const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType | null>(null);
  const [filterValues, setFilterValues] = useState<{
    date: string | null;
    store: string | null;
    status: string | null;
  }>({ date: null, store: null, status: null });

  // Data state with localStorage persistence
  // const [receipts, setReceipts] = useState<Receipt[]>(() => {
  //   const saved = localStorage.getItem("mock_receipts");
  //   return saved ? JSON.parse(saved) : [];
  // });

  // Edit Modal State
  const [selectedReceipt, setSelectedReceipt] = useState<UserReceipts | null>(
    null,
  );
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Initial fetch/sync
  // useEffect(() => {
  //   const saved = localStorage.getItem("mock_receipts");
  //   if (!saved || JSON.parse(saved).length === 0) {
  //     setReceipts(mockReceipts);
  //   }
  //   const timer = setTimeout(() => setIsLoading(false), 1000);
  //   return () => clearTimeout(timer);
  // }, []);

  // Persist changes
  // useEffect(() => {
  //   if (receipts.length > 0) {
  //     localStorage.setItem("mock_receipts", JSON.stringify(receipts));
  //   }
  // }, [receipts]);

  const { data, error, refetch, isLoading } = useQuery<UserData>({
    queryKey: ["userReceipts"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Unauthenticated");

      const res = await fetch(`${BACKEND_URL}/api/receipts`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });
      if (!res) throw new Error("Failed to fetch receipts");

      console.log("Status:", res.status);
      console.log("Response:", await res.clone().text());

      if (!res.ok) throw new Error(`Failed: ${res.status}`);

      return (await res.json()) as UserData;
    },
    staleTime: 30 * 1000,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    if (data) {
      console.log(data);
    }
  }, [data]);

  const receipts: UserReceipts[] = data?.receipts ?? [];

  // Pull to refresh handler
  const handleRefresh = async () => {
    await refetch();
  };

  const { contentRef, pullY, isRefreshing, handlers } =
    usePullToRefresh(handleRefresh);

  // Extract unique store names for filter
  const availableStores = useMemo(() => {
    const stores = [...new Set(receipts.map((r) => r.store_name))];
    return stores.sort();
  }, [receipts]);

  // Shared filter function
  const applyFilters = useCallback(
    (receipt: UserReceipts) => {
      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesStore = receipt.store_name.toLowerCase().includes(q);
        const matchesAmount = receipt.total_amount.toString().includes(q);
        const matchesItem = receipt.receipt_items.some((item) =>
          item.name.toLowerCase().includes(q),
        );
        if (!matchesStore && !matchesAmount && !matchesItem) return false;
      }

      // Status filter
      if (filterValues.status) {
        if ((receipt.status || "VERIFIED") !== filterValues.status)
          return false;
      }

      // Store filter
      if (filterValues.store) {
        if (receipt.store_name !== filterValues.store) return false;
      }

      // Date filter
      if (filterValues.date) {
        const receiptDate = new Date(receipt.transaction_date);
        const now = new Date();

        switch (filterValues.date) {
          case "today":
            if (receiptDate.toDateString() !== now.toDateString()) return false;
            break;
          case "week": {
            const weekAgo = new Date(now);
            weekAgo.setDate(weekAgo.getDate() - 7);
            if (receiptDate < weekAgo) return false;
            break;
          }
          case "month": {
            if (
              receiptDate.getMonth() !== now.getMonth() ||
              receiptDate.getFullYear() !== now.getFullYear()
            )
              return false;
            break;
          }
        }
      }

      return true;
    },
    [searchQuery, filterValues],
  );

  // Filtered Action Required receipts
  const actionRequiredResults = useMemo(() => {
    return receipts.filter(
      (r) => r.status === "ACTION_REQUIRED" && applyFilters(r),
    );
  }, [receipts, applyFilters]);

  // Filtered Recent Activity receipts (excluding action-required)
  const recentActivityResults = useMemo(() => {
    return receipts.filter(
      (r) => r.status !== "ACTION_REQUIRED" && applyFilters(r),
    );
  }, [receipts, applyFilters]);

  const hasAnyReceipts = receipts.length > 0;
  const hasActionResults = actionRequiredResults.length > 0;
  const hasRecentResults = recentActivityResults.length > 0;
  const isSearching =
    searchQuery !== "" ||
    filterValues.date !== null ||
    filterValues.store !== null ||
    filterValues.status !== null;

  const handleFilterToggle = useCallback((filter: FilterType) => {
    setActiveFilter((prev) => (prev === filter ? null : filter));
  }, []);

  const handleFilterSelect = useCallback(
    (filter: FilterType, value: string | null) => {
      setFilterValues((prev) => ({ ...prev, [filter]: value }));
      setActiveFilter(null);
    },
    [],
  );

  const handleReviewReceipt = useCallback((receipt: UserReceipts) => {
    setSelectedReceipt(receipt);
    setIsEditModalOpen(true);
  }, []);

  const handleStatusClick = useCallback(
    (receipt: UserReceipts) => {
      if (receipt.status === "VERIFIED" || receipt.status === "PENDING") {
        handleReviewReceipt(receipt);
      }
    },
    [handleReviewReceipt],
  );
  const handleSaveReceipt = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const handleViewAllActionRequired = () => {
    navigate({ to: "/receipts/action-required" });
  };

  const isReadOnly =
    selectedReceipt?.status === "VERIFIED" ||
    selectedReceipt?.status === "PENDING";

  if (isLoading) {
    return <ReceiptsSkeleton />;
  }

  if (error) throw new Error("Data tidak keangkut cuy...", error);

  return (
    <div
      ref={contentRef}
      className="pb-24 min-h-screen relative bg-[#0b0e11]"
      onClick={() => {
        if (activeFilter) setActiveFilter(null);
      }}
      onTouchStart={handlers.onTouchStart}
      onTouchMove={handlers.onTouchMove}
      onTouchEnd={handlers.onTouchEnd}
    >
      {/* Pull to refresh indicator */}
      <div
        className="absolute top-0 left-0 right-0 flex items-center justify-center pointer-events-none transition-transform duration-200"
        style={{
          height: "60px",
          transform: `translateY(${pullY - 60}px)`,
          opacity: Math.min(pullY / 40, 1),
        }}
      >
        {isRefreshing ? (
          <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />
        ) : (
          <div className="h-1.5 w-12 bg-gray-700 rounded-full opacity-50" />
        )}
      </div>

      <div
        style={{
          transform: `translateY(${pullY > 0 ? pullY * 0.4 : 0}px)`,
          transition: isRefreshing ? "transform 0.2s" : "none",
        }}
      >
        <ReceiptHeader />
        <ReceiptSearchBar value={searchQuery} onChange={setSearchQuery} />
        <div onClick={(e) => e.stopPropagation()}>
          <ReceiptFilterChips
            activeFilter={activeFilter}
            onFilterToggle={handleFilterToggle}
            filterValues={filterValues}
            availableStores={availableStores}
            onFilterSelect={handleFilterSelect}
          />
        </div>

        {!hasAnyReceipts ? (
          <ReceiptEmptyState type="no-receipts" />
        ) : (
          <>
            {!isSearching && hasActionResults && (
              <ActionRequiredSection
                receipts={actionRequiredResults}
                onViewAll={handleViewAllActionRequired}
                onReviewReceipt={handleReviewReceipt}
              />
            )}

            {!hasRecentResults && isSearching ? (
              <ReceiptEmptyState type="no-results" />
            ) : (
              <RecentActivityList
                receipts={recentActivityResults}
                onReceiptClick={handleReviewReceipt}
                onStatusClick={handleStatusClick}
              />
            )}
          </>
        )}
      </div>

      {/* Edit Modal */}
      {selectedReceipt && isEditModalOpen && (
        <ReceiptEditModal
          key={selectedReceipt.id}
          receipt={selectedReceipt}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSaveReceipt}
          isReadOnly={isReadOnly}
        />
      )}
    </div>
  );
};
