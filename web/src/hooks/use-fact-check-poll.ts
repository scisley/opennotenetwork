import { useEffect, useState, useRef } from "react";
import { useAuthenticatedApi } from "@/lib/auth-axios";
import { type VerdictOrNull } from "@/lib/verdict";

export interface NodeUpdate {
  node: string;
  data: any;
  timestamp: number;
}

interface FactCheckState {
  id: string | null;
  status: "pending" | "processing" | "completed" | "failed" | null;
  updates: NodeUpdate[];
  verdict: VerdictOrNull;
  confidence: number | undefined;
  body: string | null;
  error: string | null;
}

export function useFactCheckPoll(
  postUid: string,
  factCheckerSlug: string,
  enabled: boolean = true
) {
  const [state, setState] = useState<FactCheckState>({
    id: null,
    status: null,
    updates: [],
    verdict: null,
    confidence: undefined,
    body: null,
    error: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const authApi = useAuthenticatedApi();

  // Function to process updates from raw_json
  const processRawJson = (rawJson: any): NodeUpdate[] => {
    if (!rawJson || !rawJson.updates) return [];
    
    const updates: NodeUpdate[] = [];
    
    // Process the serialized updates
    for (const update of rawJson.updates) {
      // Each update is a serialized chunk from LangGraph
      if (update && typeof update === 'object') {
        // Extract node name and data from the update
        const nodeNames = Object.keys(update);
        for (const nodeName of nodeNames) {
          updates.push({
            node: nodeName,
            data: update[nodeName],
            timestamp: Date.now(),
          });
        }
      }
    }
    
    return updates;
  };

  // Function to start or run a fact check
  const startFactCheck = async () => {
    try {
      const response = await authApi.post(
        `/api/admin/posts/${postUid}/fact-check/${factCheckerSlug}`
      );
      
      const data = response.data;
      setState(prev => ({
        ...prev,
        id: data.id,
        status: data.status,
        error: null,
      }));
      
      // Start polling if the status is pending or processing
      if (data.status === "pending" || data.status === "processing") {
        startPolling(data.id);
      }
    } catch (err) {
      console.error("Failed to start fact check:", err);
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : "Failed to start fact check",
      }));
    }
  };

  // Function to poll for updates
  const pollFactCheck = async (factCheckId: string) => {
    try {
      const response = await authApi.get(
        `/api/admin/fact-checks/${factCheckId}/status`
      );
      
      const data = response.data;
      
      // Process updates from raw_json
      const updates = processRawJson(data.raw_json);
      
      setState(prev => ({
        ...prev,
        status: data.status,
        updates: updates.length > 0 ? updates : prev.updates,
        verdict: data.verdict,
        confidence: data.confidence,
        body: data.body,
        error: data.error_message || null,
      }));
      
      // Stop polling if complete or failed
      if (data.status === "completed" || data.status === "failed") {
        stopPolling();
      }
    } catch (err) {
      console.error("Failed to poll fact check:", err);
      // Don't stop polling on error, just log it
    }
  };

  // Function to start polling
  const startPolling = (factCheckId: string) => {
    // Clear any existing interval
    stopPolling();
    
    // Poll immediately
    pollFactCheck(factCheckId);
    
    // Then poll every 5 seconds
    intervalRef.current = setInterval(() => {
      pollFactCheck(factCheckId);
    }, 5000);
  };

  // Function to stop polling
  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Check for existing fact check on mount
  useEffect(() => {
    if (!enabled) return;

    const checkExisting = async () => {
      try {
        // First, check if a fact check already exists  
        const response = await authApi.get(
          `/api/posts/${postUid}/fact-checks`
        );
        
        const factChecks = response.data.fact_checks || [];
        const existing = factChecks.find(
          (check: any) => check.fact_checker.slug === factCheckerSlug
        );
        
        if (existing) {
          // Process existing fact check
          const updates = processRawJson(existing.raw_json);
          
          setState({
            id: existing.id,
            status: existing.status,
            updates,
            verdict: existing.verdict,
            confidence: existing.confidence,
            body: existing.body,
            error: existing.error_message || null,
          });
          
          // Start polling if still processing
          if (existing.status === "pending" || existing.status === "processing") {
            startPolling(existing.id);
          }
        } else {
          // No existing fact check, start a new one
          startFactCheck();
        }
      } catch (err) {
        console.error("Failed to check existing fact checks:", err);
        setState(prev => ({
          ...prev,
          error: err instanceof Error ? err.message : "Failed to load fact check",
        }));
      }
    };

    checkExisting();

    // Cleanup on unmount
    return () => {
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postUid, factCheckerSlug, enabled]);

  return {
    factCheckId: state.id,
    status: state.status,
    updates: state.updates,
    verdict: state.verdict,
    confidence: state.confidence,
    body: state.body,
    error: state.error,
    isComplete: state.status === "completed",
    isFailed: state.status === "failed",
    isProcessing: state.status === "processing" || state.status === "pending",
  };
}