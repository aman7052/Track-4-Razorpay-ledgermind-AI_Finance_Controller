import time
from typing import Union, BinaryIO, Dict, Any, List
from schemas.models import (
    InvoiceData, 
    ReconciliationReport, 
    AnomalyRiskReport, 
    SettlementPlan
)
from agents.invoice_parser import InvoiceParserAgent
from agents.reconciliation import ReconciliationAgent
from agents.anomaly_auditor import AnomalyAuditAgent
from agents.settlement import SettlementAgent

class AgentExecutionStep:
    def __init__(self, step_name: str, agent_name: str, description: str):
        self.step_name = step_name
        self.agent_name = agent_name
        self.description = description
        self.status = "PENDING"  # PENDING, RUNNING, SUCCESS, WARNING, FAILED
        self.start_time = 0.0
        self.duration_ms = 0.0
        self.output_summary = ""
        self.details: Dict[str, Any] = {}

class LedgerMindWorkflowResult:
    def __init__(self):
        self.invoice: InvoiceData = None
        self.reconciliation: ReconciliationReport = None
        self.risk_report: AnomalyRiskReport = None
        self.settlement: SettlementPlan = None
        self.steps: List[AgentExecutionStep] = []
        self.total_duration_ms: float = 0.0

class MultiAgentController:
    """
    Master Orchestration Engine coordinating the 4 autonomous financial agents.
    Tracks step-by-step state and execution telemetry for real-time UI visualization.
    """
    def __init__(self, llm_provider: str = "auto", auto_payout_threshold: float = 20.0):
        self.llm_provider = llm_provider
        self.auto_payout_threshold = auto_payout_threshold
        self.parser_agent = InvoiceParserAgent(llm_provider=llm_provider)
        self.recon_agent = ReconciliationAgent()
        self.audit_agent = AnomalyAuditAgent()
        self.settlement_agent = SettlementAgent()

    def process_invoice(self, file_source: Union[str, BinaryIO, bytes]) -> LedgerMindWorkflowResult:
        workflow_start = time.time()
        result = LedgerMindWorkflowResult()

        # Step 1: Document Ingestion & Parsing
        step1 = AgentExecutionStep("Step 1: Document Ingestion", "InvoiceParserAgent", "Extracting OCR text, GSTIN, metadata, and line items")
        step1.start_time = time.time()
        step1.status = "RUNNING"
        try:
            invoice_data = self.parser_agent.parse_invoice(file_source)
            result.invoice = invoice_data
            step1.status = "SUCCESS"
            step1.output_summary = f"Parsed {len(invoice_data.line_items)} line items from {invoice_data.vendor_name} (Inv: {invoice_data.invoice_number})"
            step1.details = {
                "vendor_name": invoice_data.vendor_name,
                "invoice_number": invoice_data.invoice_number,
                "total_amount": invoice_data.total_amount,
                "gstin": invoice_data.vendor_gstin,
                "po_ref": invoice_data.po_reference
            }
        except Exception as e:
            step1.status = "FAILED"
            step1.output_summary = f"Parsing Error: {str(e)}"
            result.steps.append(step1)
            return result
        finally:
            step1.duration_ms = round((time.time() - step1.start_time) * 1000, 1)
            result.steps.append(step1)

        # Step 2: 3-Way Match Reconciliation
        step2 = AgentExecutionStep("Step 2: 3-Way Match Reconciliation", "ReconciliationAgent", "Reconciling against Purchase Orders and Goods Received Notes (GRN)")
        step2.start_time = time.time()
        step2.status = "RUNNING"
        try:
            recon_report = self.recon_agent.reconcile(result.invoice)
            result.reconciliation = recon_report
            if recon_report.status == "PERFECT_MATCH":
                step2.status = "SUCCESS"
                step2.output_summary = f"100% Match with {recon_report.matched_po_id}. Zero variance."
            else:
                step2.status = "WARNING"
                step2.output_summary = f"Discrepancy detected ({recon_report.status}): Variance of ₹{recon_report.net_variance_amount:+,.2f}."
            
            step2.details = {
                "po_id": recon_report.matched_po_id,
                "status": recon_report.status,
                "variance": recon_report.net_variance_amount,
                "line_count": len(recon_report.line_matches)
            }
        except Exception as e:
            step2.status = "FAILED"
            step2.output_summary = f"Reconciliation Error: {str(e)}"
            result.steps.append(step2)
            return result
        finally:
            step2.duration_ms = round((time.time() - step2.start_time) * 1000, 1)
            result.steps.append(step2)

        # Step 3: Anomaly & Risk Audit
        step3 = AgentExecutionStep("Step 3: Forensic Anomaly Audit", "AnomalyAuditAgent", "Checking duplicate payouts, bank changes, price inflation, and GST validation")
        step3.start_time = time.time()
        step3.status = "RUNNING"
        try:
            risk_report = self.audit_agent.audit(result.invoice, result.reconciliation)
            result.risk_report = risk_report
            if risk_report.risk_level == "LOW":
                step3.status = "SUCCESS"
                step3.output_summary = f"Audit Passed. Risk Score: {risk_report.overall_risk_score}/100 (Safe)"
            elif risk_report.risk_level in ["HIGH", "CRITICAL"]:
                step3.status = "FAILED" if risk_report.is_duplicate else "WARNING"
                step3.output_summary = f"Audit Alert! Risk Score: {risk_report.overall_risk_score}/100 ({risk_report.risk_level}). {risk_report.summary_bullets[0] if risk_report.summary_bullets else ''}"
            else:
                step3.status = "WARNING"
                step3.output_summary = f"Audit Caution. Risk Score: {risk_report.overall_risk_score}/100 ({risk_report.risk_level})"

            step3.details = {
                "overall_risk_score": risk_report.overall_risk_score,
                "risk_level": risk_report.risk_level,
                "is_duplicate": risk_report.is_duplicate,
                "bank_changed": risk_report.bank_account_changed,
                "price_inflation": risk_report.price_inflation_detected
            }
        except Exception as e:
            step3.status = "FAILED"
            step3.output_summary = f"Audit Error: {str(e)}"
            result.steps.append(step3)
            return result
        finally:
            step3.duration_ms = round((time.time() - step3.start_time) * 1000, 1)
            result.steps.append(step3)

        # Step 4: Settlement Decision & Razorpay Trigger
        step4 = AgentExecutionStep("Step 4: Autonomous Settlement", "SettlementAgent", "Executing Razorpay payout or drafting itemized dispute resolution")
        step4.start_time = time.time()
        step4.status = "RUNNING"
        try:
            settlement_plan = self.settlement_agent.process_settlement(
                invoice=result.invoice,
                recon_report=result.reconciliation,
                risk_report=result.risk_report,
                auto_payout_threshold=self.auto_payout_threshold
            )
            result.settlement = settlement_plan

            if settlement_plan.decision == "AUTO_PAYOUT_TRIGGERED" and settlement_plan.payout_response:
                step4.status = "SUCCESS"
                step4.output_summary = f"Instant Payout Processed! UTR: {settlement_plan.payout_response.utr}, TDS: ₹{settlement_plan.tds_deduction_amount:,.2f}, Net: ₹{settlement_plan.net_payable_amount:,.2f}"
            else:
                step4.status = "WARNING"
                step4.output_summary = f"Payment Held ({settlement_plan.decision}). Auto-drafted dispute notice for vendor."

            step4.details = {
                "decision": settlement_plan.decision,
                "net_payable": settlement_plan.net_payable_amount,
                "payout_id": settlement_plan.payout_response.payout_id if settlement_plan.payout_response else None,
                "utr": settlement_plan.payout_response.utr if settlement_plan.payout_response else None
            }
        except Exception as e:
            step4.status = "FAILED"
            step4.output_summary = f"Settlement Error: {str(e)}"
            result.steps.append(step4)
            return result
        finally:
            step4.duration_ms = round((time.time() - step4.start_time) * 1000, 1)
            result.steps.append(step4)

        result.total_duration_ms = round((time.time() - workflow_start) * 1000, 1)
        return result
