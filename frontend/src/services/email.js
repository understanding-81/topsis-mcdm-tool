import emailjs from "@emailjs/browser";

export const sendResultEmail = async (toEmail, resultLink) => {
  return emailjs.send(
    "YOUR_SERVICE_ID",
    "YOUR_TEMPLATE_ID",
    {
      to_email: toEmail,
      result_link: resultLink,
    },
    "YOUR_PUBLIC_KEY"
  );
};
