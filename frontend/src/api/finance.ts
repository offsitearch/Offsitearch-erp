import { UPLOAD_TIMEOUT_MS, api } from './client';
import type {
  Expense,
  FinanceOverview,
  Invoice,
  InvoiceCreateInput,
  PaymentMethod,
  PayrollRun,
} from '../lib/types';

export interface InvoiceListParams {
  status?: string;
  client_id?: number;
  search?: string;
}

/** Fetches a filtered list of invoices. */
export async function getInvoices(params: InvoiceListParams = {}): Promise<Invoice[]> {
  const { data } = await api.get<{ items: Invoice[] }>('/invoices', { params });
  return data.items ?? [];
}

/** Fetches a single invoice by ID. */
export async function getInvoice(id: number): Promise<Invoice> {
  const { data } = await api.get<Invoice>(`/invoices/${id}`);
  return data;
}

/** Creates a new invoice. */
export async function createInvoice(payload: InvoiceCreateInput): Promise<Invoice> {
  const { data } = await api.post<Invoice>('/invoices', payload);
  return data;
}

/** Updates an existing invoice. */
export async function updateInvoice(id: number, payload: Partial<InvoiceCreateInput>): Promise<Invoice> {
  const { data } = await api.patch<Invoice>(`/invoices/${id}`, payload);
  return data;
}

/** Sends an invoice to the client. */
export async function sendInvoice(id: number): Promise<Invoice> {
  const { data } = await api.post<Invoice>(`/invoices/${id}/send`);
  return data;
}

/** Records a payment against an invoice. */
export async function recordInvoicePayment(
  id: number,
  payload: { amount: number; payment_date: string; method: PaymentMethod },
): Promise<Invoice> {
  const { data } = await api.post<Invoice>(`/invoices/${id}/payment`, payload);
  return data;
}

/** Downloads an invoice as a PDF file. */
export async function downloadInvoicePdf(id: number): Promise<void> {
  const response = await api.get(`/invoices/${id}/pdf`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `invoice-${id}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

export interface ExpenseCreateInput {
  category: string;
  amount: number;
  description?: string;
  expense_date?: string;
  project_id?: number | null;
  paid_by?: string;
}

/** Fetches a filtered list of expenses. */
export async function getExpenses(params: { status?: string; category?: string } = {}): Promise<Expense[]> {
  const { data } = await api.get<{ items: Expense[] }>('/expenses', { params });
  return data.items ?? [];
}

/** Creates a new expense record. */
export async function createExpense(payload: ExpenseCreateInput): Promise<Expense> {
  const { data } = await api.post<Expense>('/expenses', payload);
  return data;
}

/** Approves or rejects an expense record. */
export async function approveExpense(id: number, approve: boolean): Promise<Expense> {
  const { data } = await api.patch<Expense>(`/expenses/${id}/approve`, { approve });
  return data;
}

/** Uploads a receipt file for an expense. */
export async function uploadExpenseReceipt(id: number, file: File): Promise<Expense> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<Expense>(`/expenses/${id}/receipt`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  });
  return data;
}

/** Downloads the receipt for an expense as a blob. */
export async function downloadExpenseReceipt(id: number): Promise<void> {
  const response = await api.get(`/expenses/${id}/receipt`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

/** Fetches payroll data for a given month and year. */
export async function getPayroll(month: number, year: number): Promise<PayrollRun> {
  const { data } = await api.get<PayrollRun>('/payroll', { params: { month, year } });
  return data;
}

/** Triggers payroll processing for a given month and year. */
export async function processPayroll(month: number, year: number): Promise<PayrollRun> {
  const { data } = await api.post<PayrollRun>('/payroll/process', { month, year });
  return data;
}

/** Downloads an employee's payslip as a PDF file. */
export async function downloadPayslip(userId: number, month: number, year: number): Promise<void> {
  const response = await api.get(`/payroll/${month}/${year}/payslips/${userId}`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

/** Fetches the finance overview dashboard data for a period. */
export async function getFinanceOverview(period: string, compare = false): Promise<FinanceOverview> {
  const { data } = await api.get<FinanceOverview>('/finance/overview', {
    params: { period, compare },
  });
  return data;
}

/** Fetches the current user's own expenses with optional filters. */
export async function getMyExpenses(filters?: { category?: string; status?: string; month?: number; year?: number }) {
  const params = new URLSearchParams();
  if (filters?.category) params.set('category', filters.category);
  if (filters?.status) params.set('status', filters.status);
  if (filters?.month) params.set('month', String(filters.month));
  if (filters?.year) params.set('year', String(filters.year));
  const { data } = await api.get<{ items: Expense[] }>(`/finance/my-expenses?${params.toString()}`);
  return data.items ?? [];
}

/** Creates a new expense record for the current user. */
export async function createMyExpense(payload: { category: string; description?: string; amount: number; expense_date?: string; project_id?: number }) {
  const { data } = await api.post('/finance/my-expenses', payload);
  return data;
}
