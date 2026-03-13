import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

export type FilterType = "date" | "store" | "status";

interface ReceiptFilterChipsProps {
  activeFilter: FilterType | null;
  onFilterToggle: (filter: FilterType) => void;
  filterValues: {
    date: string | null;
    store: string | null;
    status: string | null;
  };
  availableStores: string[];
  onFilterSelect: (filter: FilterType, value: string | null) => void;
}

const statusOptions = [
  { label: "All", value: null },
  { label: "Pending", value: "pending" },
  { label: "Verified", value: "verified" },
  { label: "Split", value: "split" },
];

const dateOptions = [
  { label: "All", value: null },
  { label: "Today", value: "today" },
  { label: "This Week", value: "week" },
  { label: "This Month", value: "month" },
];

export const ReceiptFilterChips = ({
  activeFilter,
  onFilterToggle,
  filterValues,
  availableStores,
  onFilterSelect,
}: ReceiptFilterChipsProps) => {
  const filters: { id: FilterType; label: string }[] = [
    {
      id: "date",
      label: filterValues.date ? getDateLabel(filterValues.date) : "Date",
    },
    { id: "store", label: filterValues.store || "Store" },
    {
      id: "status",
      label: filterValues.status ? capitalize(filterValues.status) : "Status",
    },
  ];

  return (
    <div className="px-4 pb-4">
      <div className="flex gap-2">
        {filters.map((filter) => {
          const isActive = filterValues[filter.id] !== null;
          return (
            <div key={filter.id} className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onFilterToggle(filter.id)}
                className={`rounded-full border-gray-600 text-sm px-4 py-2 h-auto transition-colors ${
                  isActive
                    ? "bg-blue-500/20 border-blue-500/50 text-blue-400"
                    : "bg-[#1a2129] text-gray-300 hover:bg-[#232d38]"
                }`}
              >
                {filter.label}
                <ChevronDown
                  className={`h-3 w-3 ml-1 transition-transform ${activeFilter === filter.id ? "rotate-180" : ""}`}
                />
              </Button>

              {/* Dropdown */}
              {activeFilter === filter.id && (
                <div className="absolute top-full left-0 mt-2 bg-[#1a2129] border border-gray-700 rounded-xl py-2 min-w-35 max-w-55 overflow-auto z-999 shadow-xl">
                  {filter.id === "status" &&
                    statusOptions.map((opt) => (
                      <button
                        key={opt.label}
                        onClick={() => onFilterSelect("status", opt.value)}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                          filterValues.status === opt.value
                            ? "text-blue-400 bg-blue-500/10"
                            : "text-gray-300 hover:bg-[#232d38]"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}

                  {filter.id === "date" &&
                    dateOptions.map((opt) => (
                      <button
                        key={opt.label}
                        onClick={() => onFilterSelect("date", opt.value)}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                          filterValues.date === opt.value
                            ? "text-blue-400 bg-blue-500/10"
                            : "text-gray-300 hover:bg-[#232d38]"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}

                  {filter.id === "store" && (
                    <>
                      <button
                        onClick={() => onFilterSelect("store", null)}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                          filterValues.store === null
                            ? "text-blue-400 bg-blue-500/10"
                            : "text-gray-300 hover:bg-[#232d38]"
                        }`}
                      >
                        All
                      </button>
                      {availableStores.map((store) => (
                        <button
                          key={store}
                          onClick={() => onFilterSelect("store", store)}
                          className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                            filterValues.store === store
                              ? "text-blue-400 bg-blue-500/10"
                              : "text-gray-300 hover:bg-[#232d38]"
                          }`}
                        >
                          {store}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function getDateLabel(value: string): string {
  switch (value) {
    case "today":
      return "Today";
    case "week":
      return "This Week";
    case "month":
      return "This Month";
    default:
      return "Date";
  }
}
