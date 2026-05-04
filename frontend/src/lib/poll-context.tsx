import React, { createContext, useContext, useState } from "react"
import type { PollMode } from "@/types"

interface PollContextType {
    pollMode: PollMode
    setPollMode: (mode: PollMode) => void
}

const PollContext = createContext<PollContextType | undefined>(undefined)

export function PollProvider({ children }: { children: React.ReactNode }) {
    const [pollMode, setPollMode] = useState<PollMode>("realtime")
    return (
        <PollContext.Provider value={{ pollMode, setPollMode }}>
            {children}
        </PollContext.Provider>
    )
}

export function usePollMode() {
    const context = useContext(PollContext)
    if (context === undefined) {
        throw new Error("usePollMode must be used within a PollProvider")
    }
    return context
}
