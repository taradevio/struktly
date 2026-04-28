import { useState, useEffect, useMemo } from "react";
import { CustomTooltip } from "./CustomChartTooltip";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { formattedRupiah } from "@/utils/currency";
import { setToken } from "@/lib/auth";
// import { transformCategoryData } from "@/utils/categoryHelpers";

// import { useQuery } from "@tanstack/react-query";
import { Bell, TrendingUp } from "lucide-react";
import { Card, CardContent } from "./ui/card";
// import { Input } from "./ui/input";
import { Button } from "./ui/button";
// import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { Skeleton } from "./ui/skeleton";
import {
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  //   ReferenceLine,
  Line,
  ComposedChart,
} from "recharts";

// Weekly budget limit (monthly / 4)
// const weeklyBudgetLimit = 750;

interface TelegramUser {
  first_name: string;
  photo_url?: string;
  id?: string;
}

interface ReceiptItem {
  id: string;
  name: string;
  qty: number;
  price: number;
  total_price: number;
  category: string;
  created_at: string;
}

interface UserReceipts {
  id: string;
  store_name: string;
  total_amount: number;
  transaction_date: string;
  receipt_items: ReceiptItem[];
}

const queryClient = new QueryClient();

const chartData = [
  { week: "Week 1", spending: 450, budget: 750, predicted: null },
  { week: "Week 2", spending: 520, budget: 750, predicted: null },
  { week: "Week 3", spending: 680, budget: 750, predicted: 680 },
  { week: "Week 4", spending: null, budget: 750, predicted: 800 },
];

// const storeData = [
//   {
//     id: 1,
//     name: "Walmart",
//     logo: "W",
//     bgColor: "bg-green-600",
//     transactions: 8,
//     amount: 432.5,
//     change: 12.5,
//     isUp: true,
//   },
//   {
//     id: 2,
//     name: "Amazon",
//     logo: "a",
//     bgColor: "bg-gradient-to-br from-gray-800 to-yellow-600",
//     transactions: 14,
//     amount: 289.9,
//     change: 3.2,
//     isUp: false,
//   },
//   {
//     id: 3,
//     name: "Target",
//     logo: "◎",
//     bgColor: "bg-red-600",
//     transactions: 3,
//     amount: 145.2,
//     change: 8.4,
//     isUp: true,
//   },
// ];

// Budget data
const budgetData = {
  monthly: 3000,
  spent: 2450,
  remaining: 550,
  percentage: 81.7,
};

// Category spending data
// const categoryData = [
//   {
//     id: 1,
//     name: "Food & Dining",
//     icon: "🍔",
//     amount: 820.5,
//     percentage: 33.5,
//     color: "bg-orange-500",
//   },
//   {
//     id: 2,
//     name: "Transport",
//     icon: "🚗",
//     amount: 450.0,
//     percentage: 18.4,
//     color: "bg-blue-500",
//   },
//   {
//     id: 3,
//     name: "Entertainment",
//     icon: "🎮",
//     amount: 380.0,
//     percentage: 15.5,
//     color: "bg-purple-500",
//   },
//   {
//     id: 4,
//     name: "Shopping",
//     icon: "🛍️",
//     amount: 520.0,
//     percentage: 21.2,
//     color: "bg-pink-500",
//   },
//   {
//     id: 5,
//     name: "Bills & Utilities",
//     icon: "💡",
//     amount: 279.5,
//     percentage: 11.4,
//     color: "bg-green-500",
//   },
// ];

// const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

// const fetchUserData = async () => {
//   const response = await fetch(`${BACKEND_URL}/api/user-data`, {
//     method: "GET",
//     headers: {
//       "Content-Type": "application/json",
//       credentials: "include",
//     },
//   });

//   if (!response.ok) {
//     throw new Error("Failed to fetch user data");
//   }

//   return response.json();
// };

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

export const Dashboard = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <UserDashboard />
    </QueryClientProvider>
  );
};

const UserDashboard = () => {
  // const [searchOpen, setSearchOpen] = useState(false);
  const [userReceipts, setUserReceipts] = useState<string | null>(null);
  const [userReceiptsItem, setUserReceiptsItem] = useState<UserReceipts[]>([]);
  const [telegramUserProfile, setTelegramUserProfile] =
    useState<TelegramUser | null>(null);
  const [photoUrl, SetPhotoUrl] = useState<string | null>(null);
  // const [isLoading, setIsLoading] = useState(true);
  const [focusedData, setFocusedData] = useState<{
    week: string;
    spending: number | null;
    budget: number;
    predicted: number | null;
  } | null>(null);

  // Simulate data loading
  // useEffect(() => {
  //   const timer = setTimeout(() => setIsLoading(false), 2000);
  //   return () => clearTimeout(timer);
  // }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const telegram = (window as any).Telegram.WebApp;

        if (!telegram) {
          console.error("Telegram WebApp not found");
          return;
        }

        const initData = telegram.initData;
        if (!initData) {
          console.error("bukan telegram");
          return;
        }
        console.log("init data", initData);
        setUserReceipts(initData);

        telegram.ready();
        const params = new URLSearchParams(initData);
        const userId = params.get("user");

        if (userId) {
          try {
            const decodeUser = JSON.parse(decodeURIComponent(userId));
            SetPhotoUrl(decodeUser.photo_url);
            // console.log("decoded user", decodeUser);
            // console.log("user data", userData);
          } catch (error) {
            console.error("error decoding user data", error);
          }
        }
      } catch (error) {
        console.log("error getting telegram data", error);
      }
    };

    fetchData();
  }, []);

  const { data, error, isLoading } = useQuery({
    queryKey: ["userReceipts", userReceipts],
    queryFn: async () => {
      const res = await fetch(`${BACKEND_URL}/api/user-data`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ userData: userReceipts }),
      });

      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    enabled: !!userReceipts,
  });

  useEffect(() => {
    if (data) {
      setTelegramUserProfile(data.userProfile);
      setUserReceiptsItem(data.userReceipts);

      (async () => {
        await setToken(data.accessToken);
        console.log("Token set:", sessionStorage.getItem("access_token"));
      })();
      // setTelegramUser(data.userReceipts);
      console.log("data", userReceipts);
      // console.log("telegramUser:", telegramUserProfile);
    }
  }, [data]);

  // const groupedStores = useMemo(() => {
  //   const storeMap = userReceipts.reduce((acc, item) => {
  //     const key = item.store_name.trim().toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase())

  //     if(!acc[key]) {
  //       acc[key] = {
  //         store_name : key,
  //         transaction_count: 0,
  //         receipts: []
  //       }
  //     }

  //     acc[key].transaction_count += 1;
  //     acc]key].receipts.push[receipt]
  //   })
  // }, [userReceipts])

  const groupedStores = useMemo(() => {
    const storeMap = userReceiptsItem.reduce(
      (acc, receipt) => {
        const key = receipt.store_name
          .trim()
          .toLowerCase()
          .replace(/\b\w/g, (char) => char.toUpperCase());

        if (!acc[key]) {
          acc[key] = {
            store_name: key,
            transaction_count: 0,
            total_amount: 0,
            receipts: [],
          };
        }

        acc[key].transaction_count += 1;
        acc[key].total_amount += receipt.total_amount;
        acc[key].receipts.push(receipt); // optional, kalo lo mau drill down nanti

        return acc;
      },
      {} as Record<
        string,
        {
          store_name: string;
          transaction_count: number;
          total_amount: number;
          receipts: typeof userReceiptsItem;
        }
      >,
    );

    return Object.values(storeMap);
  }, [userReceiptsItem]);
  const flatItems = userReceiptsItem?.flatMap(
    (receipt) => receipt.receipt_items,
  );
  console.log("userReceipts", userReceipts);

  // const mapItems = flatItems.map((item) => item.total)

  const categoryTotals = flatItems.reduce(
    (acc, item) => {
      acc[item.category] = (acc[item.category] || 0) + item.total_price;
      return acc;
    },
    {} as Record<string, number>,
  );

  console.log("category", categoryTotals);

  if (error) return "Data dari db kagak keangkut coy...";

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-6 pb-4">
        <div className="flex items-center gap-3">
          {isLoading ? (
            <Skeleton className="h-10 w-32 bg-gray-700" />
          ) : (
            <img
              src={photoUrl || "/avatar.png"}
              alt="Avatar"
              className="h-12 w-12 rounded-full border-2 border-gray-600 object-cover"
              referrerPolicy="no-referrer"
            />
          )}
          {/* <Avatar className="h-12 w-12 border-2 border-gray-600">
            <AvatarImage src="/avatar.png" alt="Alex" />
            <AvatarFallback className="bg-gray-700 text-white">
              👨
            </AvatarFallback>
          </Avatar> */}
          <div>
            <p className="text-xs text-gray-300 uppercase tracking-wide">
              Welcome Back
            </p>
            <h1 className="text-lg font-semibold">
              {isLoading ? (
                <Skeleton className="h-10 w-32 bg-gray-700" />
              ) : (
                `Hello ${telegramUserProfile?.first_name}`
              )}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* <Button
            variant="ghost"
            size="icon"
            className="text-gray-300 hover:text-white"
            onClick={() => setSearchOpen(!searchOpen)}
          >
            <Search className="h-5 w-5" />
          </Button> */}
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-300 hover:text-white"
          >
            <Bell className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Collapsible Search Bar */}
      {/* {searchOpen && (
        <div className="px-4 pb-4 animate-in slide-in-from-top-2 duration-200">
          <div className="relative flex items-center">
            <Search className="absolute left-3 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search transactions..."
              className="w-full bg-[#1a2129] border-none pl-10 pr-12 py-5 rounded-xl text-gray-200 placeholder:text-gray-400"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-2 text-gray-300"
              onClick={() => setSearchOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )} */}

      {/* Stats Card */}
      <div className="px-4 pb-4">
        <Card className="bg-[#1a2129] border-none rounded-2xl overflow-hidden text-white">
          <CardContent className="p-5">
            {isLoading ? (
              <div className="space-y-4">
                <div className="flex justify-between">
                  <Skeleton className="h-10 w-32 bg-gray-700" />
                  <Skeleton className="h-10 w-24 bg-gray-700" />
                </div>
                <Skeleton className="h-12 w-full bg-gray-700" />
                <Skeleton className="h-36 w-full bg-gray-700" />
              </div>
            ) : (
              <>
                {/* Stats Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-xs text-gray-300 mb-1">
                      Month over Month
                    </p>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-blue-400">
                        +5.2%
                      </span>
                      <span className="text-sm text-gray-300">
                        vs last month
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-300 mb-1">Total Spent</p>
                    <span className="text-2xl font-bold">Rp2,450.00</span>
                  </div>
                </div>

                {/* Spending Info */}
                <div className="flex items-center gap-2 mb-6 bg-[#232d38] rounded-lg px-3 py-2">
                  <div className="p-1.5 bg-green-500/20 rounded-lg">
                    <TrendingUp className="h-4 w-4 text-green-400" />
                  </div>
                  <p className="text-sm text-gray-300">
                    Your spending is{" "}
                    <span className="text-red-400 font-medium">
                      Rp121.50 higher
                    </span>{" "}
                    than the same time last month.
                  </p>
                </div>

                {/* Chart */}
                <div className="relative">
                  {/* Fixed Header Tooltip / Info Bar */}
                  <div className="absolute top-7.5 left-0 right-0 flex justify-center z-10 h-8">
                    {focusedData ? (
                      <Badge
                        className={`text-xs px-3 py-1 rounded-full transition-colors duration-200 ${
                          (focusedData.spending || 0) > focusedData.budget
                            ? "bg-red-500/20 text-red-400 border border-red-500/50"
                            : "bg-blue-500 text-white"
                        }`}
                      >
                        <span className="font-semibold mr-1">
                          {focusedData.week}
                        </span>
                        <span className="mx-1">
                          Actual: Rp{focusedData.spending ?? "-"}
                        </span>
                        <span className="mx-1 opacity-70">
                          / Budget: ${focusedData.budget}
                        </span>
                      </Badge>
                    ) : (
                      <Badge className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
                        +12% vs Oct
                      </Badge>
                    )}
                  </div>

                  <div className="h-44 mt-8">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart
                        data={chartData}
                        margin={{ left: 10, right: 10 }}
                        onMouseLeave={() => setFocusedData(null)}
                      >
                        <defs>
                          <linearGradient
                            id="colorSpending"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="5%"
                              stopColor="#3b82f6"
                              stopOpacity={0.3}
                            />
                            <stop
                              offset="95%"
                              stopColor="#3b82f6"
                              stopOpacity={0}
                            />
                          </linearGradient>
                          <linearGradient
                            id="colorBudget"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="5%"
                              stopColor="#64748b"
                              stopOpacity={0.2}
                            />
                            <stop
                              offset="95%"
                              stopColor="#64748b"
                              stopOpacity={0.1}
                            />
                          </linearGradient>
                        </defs>
                        <XAxis
                          dataKey="week"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#9ca3af", fontSize: 12 }}
                          interval={0}
                          padding={{ left: 20, right: 20 }}
                        />
                        <YAxis hide domain={[0, 900]} />

                        <Tooltip
                          content={
                            <CustomTooltip setFocusedData={setFocusedData} />
                          }
                          cursor={{ stroke: "#ffffff20", strokeWidth: 1 }}
                        />

                        {/* Budget Layer (Background) */}
                        <Area
                          type="monotone"
                          dataKey="budget"
                          stroke="none"
                          fill="url(#colorBudget)"
                          fillOpacity={1}
                        />

                        {/* Actual spending area (Foreground) */}
                        <Area
                          type="monotone"
                          dataKey="spending"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          fill="url(#colorSpending)"
                          connectNulls={false}
                        />
                        {/* Predicted spending line (dotted) */}
                        <Line
                          type="monotone"
                          dataKey="predicted"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          strokeDasharray="5 5"
                          dot={{ fill: "#3b82f6", strokeWidth: 0, r: 4 }}
                          connectNulls
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Budget Progress */}
      <div className="px-4 pb-4">
        <Card className="bg-[#1a2129] border-none rounded-2xl text-white">
          <CardContent className="p-5">
            {isLoading ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-24 bg-gray-700" />
                  <Skeleton className="h-6 w-20 bg-gray-700" />
                </div>
                <Skeleton className="h-3 w-full bg-gray-700" />
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-20 bg-gray-700" />
                  <Skeleton className="h-4 w-20 bg-gray-700" />
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-gray-300">
                    Monthly Budget
                  </h3>
                  <span className="text-lg font-bold">
                    ${budgetData.monthly.toLocaleString()}
                  </span>
                </div>
                <div className="relative mb-3">
                  <Progress
                    value={budgetData.percentage}
                    className="h-3 bg-gray-700"
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">
                    <span className="font-semibold text-white">
                      ${budgetData.spent.toLocaleString()}
                    </span>{" "}
                    spent
                  </span>
                  <span className="text-gray-300">
                    <span className="font-semibold text-green-400">
                      ${budgetData.remaining.toLocaleString()}
                    </span>{" "}
                    remaining
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown */}
      <div className="px-4 pb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Spending by Category</h2>
          <Button variant="link" className="text-blue-400 p-0 h-auto">
            See all
          </Button>
        </div>

        <Card className="bg-[#1a2129] border-none rounded-2xl text-white">
          <CardContent className="p-4 space-y-4">
            {isLoading
              ? Array(5)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="space-y-2">
                      <div className="flex justify-between">
                        <Skeleton className="h-5 w-32 bg-gray-700" />
                        <Skeleton className="h-5 w-16 bg-gray-700" />
                      </div>
                      <Skeleton className="h-2 w-full bg-gray-700" />
                    </div>
                  ))
              : Object.entries(categoryTotals).map(([category, total]) => (
                  <div key={category}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {/* <span className="text-lg">{category.icon}</span> */}
                        <span className="text-sm font-medium">{category}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-semibold">
                          {formattedRupiah(total)}
                        </span>
                        {/* <span className="text-xs text-gray-300 ml-2">
                          {category.percentage}%
                        </span> */}
                      </div>
                    </div>
                    {/* <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${category.color} rounded-full transition-all`}
                        style={{ width: `${category.percentage}%` }}
                      />
                    </div> */}
                  </div>
                ))}
          </CardContent>
        </Card>
      </div>

      {/* Spending by Store */}
      <div className="px-4 pb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Spending by Store</h2>
          <Button variant="link" className="text-blue-400 p-0 h-auto">
            See all
          </Button>
        </div>

        <div className="space-y-3">
          {isLoading
            ? Array(3)
                .fill(0)
                .map((_, i) => (
                  <Card key={i} className="bg-[#1a2129] border-none rounded-xl">
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Skeleton className="h-11 w-11 rounded-xl bg-gray-700" />
                        <div className="space-y-2">
                          <Skeleton className="h-4 w-24 bg-gray-700" />
                          <Skeleton className="h-3 w-20 bg-gray-700" />
                        </div>
                      </div>
                      <div className="space-y-2 flex flex-col items-end">
                        <Skeleton className="h-5 w-16 bg-gray-700" />
                        <Skeleton className="h-3 w-12 bg-gray-700" />
                      </div>
                    </CardContent>
                  </Card>
                ))
            : groupedStores.map((store) => (
                <Card
                  key={store.store_name}
                  className="bg-[#1a2129] border-none rounded-xl text-white"
                >
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {/* <div
                        className={`h-11 w-11 ${store.bgColor} rounded-xl flex items-center justify-center text-white font-bold text-lg`}
                      >
                        {store.logo}
                      </div> */}
                      <div>
                        <p className="font-medium">{store.store_name}</p>
                        <p className="text-sm text-gray-300">
                          {store.transaction_count} transactions
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        {formattedRupiah(store.total_amount)}
                      </p>
                      {/* <div
                        className={`flex items-center justify-end gap-1 text-sm ${
                          store.isUp ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {store.isUp ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )}
                        <span>{store.change}%</span>
                      </div> */}
                    </div>
                  </CardContent>
                </Card>
              ))}
        </div>
      </div>

      {/* Action Buttons
      <div className="px-4 pb-6 flex gap-3">
        <Button
          variant="outline"
          className="flex-1 bg-[#1a2129] border-gray-700 text-blue-400 py-6 rounded-xl hover:bg-[#232d38]"
        >
          <ArrowUpDown className="h-5 w-5 mr-2" />
          Split Bill
        </Button>
        <Button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-6 rounded-xl">
          <Upload className="h-5 w-5 mr-2" />
          Export Data
        </Button>
      </div> */}
    </div>
  );
};
