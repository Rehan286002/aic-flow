import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  DemoStore,
  type DemoState,
  type ReplacementDocMeta,
} from './demoStore';
import type { FindingStatus } from '@/features/validation/types';

interface DemoContextValue {
  demoState: DemoState;
  updateFindingStatus: (
    findingId: string,
    targetStatus: FindingStatus,
    rationale: string,
    actorName?: string
  ) => void;
  submitRectification: (docMeta: ReplacementDocMeta, clarificationText: string) => void;
  recordLeadDisposition: (
    disposition: 'PROCEED' | 'HOLD' | 'INSPECTION' | 'RETURN',
    rationale: string,
    leadAuditorName?: string
  ) => void;
  generateInspectionReferral: (
    scope: string[],
    targetStartDate: string,
    targetEndDate: string,
    instructions: string
  ) => void;
  toggleTamperEvent: (sequenceNo: number) => void;
  resetDemo: () => void;
  reloadDemo: () => void;
}

const DemoContext = createContext<DemoContextValue | null>(null);

export function DemoScenarioProvider({ children }: { children: ReactNode }) {
  const [demoState, setDemoState] = useState<DemoState>(() => DemoStore.load());

  // Listen to storage events so changes in another tab/window sync automatically
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'aic_verify_demo_state_v1') {
        setDemoState(DemoStore.load());
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const updateFindingStatus = useCallback(
    (
      findingId: string,
      targetStatus: FindingStatus,
      rationale: string,
      actorName = 'Auditor'
    ) => {
      const updated = DemoStore.updateFindingStatus(findingId, targetStatus, rationale, actorName);
      setDemoState(updated);
    },
    []
  );

  const submitRectification = useCallback(
    (docMeta: ReplacementDocMeta, clarificationText: string) => {
      const updated = DemoStore.submitRectification(docMeta, clarificationText);
      setDemoState(updated);
    },
    []
  );

  const recordLeadDisposition = useCallback(
    (
      disposition: 'PROCEED' | 'HOLD' | 'INSPECTION' | 'RETURN',
      rationale: string,
      leadAuditorName = 'Dr. H. V. Verma (Lead Auditor)'
    ) => {
      const updated = DemoStore.recordLeadDisposition(disposition, rationale, leadAuditorName);
      setDemoState(updated);
    },
    []
  );

  const generateInspectionReferral = useCallback(
    (
      scope: string[],
      targetStartDate: string,
      targetEndDate: string,
      instructions: string
    ) => {
      const updated = DemoStore.generateInspectionReferral(scope, targetStartDate, targetEndDate, instructions);
      setDemoState(updated);
    },
    []
  );

  const toggleTamperEvent = useCallback((sequenceNo: number) => {
    const updated = DemoStore.toggleTamperEvent(sequenceNo);
    setDemoState(updated);
  }, []);

  const resetDemo = useCallback(() => {
    const fresh = DemoStore.reset();
    setDemoState(fresh);
  }, []);

  const reloadDemo = useCallback(() => {
    setDemoState(DemoStore.load());
  }, []);

  return (
    <DemoContext.Provider
      value={{
        demoState,
        updateFindingStatus,
        submitRectification,
        recordLeadDisposition,
        generateInspectionReferral,
        toggleTamperEvent,
        resetDemo,
        reloadDemo,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
}

export function useDemoScenario(): DemoContextValue {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemoScenario must be used within a DemoScenarioProvider');
  }
  return context;
}
