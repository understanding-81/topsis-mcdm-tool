import emailjs from "@emailjs/browser";

export function sendResultEmail(toEmail, resultLink) {
  return emailjs.send(
    import.meta.env.VITE_EMAILJS_SERVICE_ID,
    import.meta.env.VITE_EMAILJS_TEMPLATE_ID,
    {
      to_email: toEmail,
      result_link: resultLink,
    },
    import.meta.env.VITE_EMAILJS_PUBLIC_KEY
  );
}
