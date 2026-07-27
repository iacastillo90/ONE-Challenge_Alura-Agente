import api from "@/services/api"

export interface WhatsAppSendResult {
  status: string
  to: string
}

/** Send a WhatsApp message to a specified number (or the platform default)
 *  through the backend -> n8n bridge. */
export async function sendWhatsApp(message: string, to?: string): Promise<WhatsAppSendResult> {
  const res = await api.post<WhatsAppSendResult>("/webhooks/whatsapp/send", {
    message,
    to: to || undefined,
  })
  return res.data
}
