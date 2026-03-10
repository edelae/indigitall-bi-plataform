import { createContext, useContext, useState, type ReactNode } from 'react'

interface DateRange {
  startDate: string
  endDate: string
}

interface DateFilterCtx {
  dateRange: DateRange
  setDateRange: (range: DateRange) => void
  dateParams: { start_date?: string; end_date?: string }
}

const DateFilterContext = createContext<DateFilterCtx>({
  dateRange: { startDate: '', endDate: '' },
  setDateRange: () => {},
  dateParams: {},
})

export function DateFilterProvider({ children }: { children: ReactNode }) {
  const [dateRange, setDateRange] = useState<DateRange>({ startDate: '', endDate: '' })

  const dateParams = {
    start_date: dateRange.startDate || undefined,
    end_date: dateRange.endDate || undefined,
  }

  return (
    <DateFilterContext.Provider value={{ dateRange, setDateRange, dateParams }}>
      {children}
    </DateFilterContext.Provider>
  )
}

export function useDateFilter() {
  return useContext(DateFilterContext)
}
