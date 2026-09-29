/* Inline card setup (Stripe.js Elements) for the signup payment step.
 *
 * The card number/CVC go browser -> Stripe only. This module sees the
 * SetupIntent id, never card data. Server endpoints (JSON):
 *   POST billing/setup-intent/  {plan}            -> {client_secret, ...}
 *   POST billing/confirm-card/  {setup_intent_id} -> {next}
 */

declare const Stripe: any;

function csrfToken(): string {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
}

function postJSON(url: string, body: Record<string, string>): Promise<{ status: number; data: any }> {
    return fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(body || {}),
        credentials: "same-origin",
    }).then((resp) =>
        resp.json().then((data) => ({ status: resp.status, data: data })),
    );
}

function ready(fn: () => void): void {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

ready(() => {
    const form = document.getElementById("inline-card-form") as HTMLFormElement | null;
    if (!form || typeof Stripe === "undefined") return;

    const publishableKey = form.dataset.publishableKey || "";
    const intentUrl = form.dataset.intentUrl || "";
    const confirmUrl = form.dataset.confirmUrl || "";
    const plan = form.dataset.plan || "";
    if (!publishableKey || !intentUrl || !confirmUrl) return;

    const stripe = Stripe(publishableKey);
    const elements = stripe.elements();
    const style = {
        base: { fontSize: "16px", color: "#1a1a1a" },
        invalid: { color: "#b42318" },
    };
    const number = elements.create("cardNumber", { style: style });
    const expiry = elements.create("cardExpiry", { style: style });
    const cvc = elements.create("cardCvc", { style: style });
    number.mount("#inline-card-number");
    expiry.mount("#inline-card-expiry");
    cvc.mount("#inline-card-cvc");

    const errorBox = document.getElementById("inline-card-errors");
    const submit = document.getElementById("inline-card-submit") as HTMLButtonElement;
    let busy = false;

    function fail(message: string): void {
        busy = false;
        submit.disabled = false;
        submit.textContent = submit.dataset.label || submit.textContent;
        if (errorBox) {
            errorBox.textContent = message;
            errorBox.hidden = false;
        }
    }

    form.addEventListener("submit", (ev) => {
        ev.preventDefault();
        if (busy) return;
        busy = true;
        submit.disabled = true;
        if (submit.dataset.label === undefined) submit.dataset.label = submit.textContent;
        submit.textContent = submit.dataset.busyLabel || "Saving your card…";
        if (errorBox) errorBox.hidden = true;

        postJSON(intentUrl, { plan: plan })
            .then((intentResp) => {
                if (!intentResp.data.ok) {
                    fail("We could not start card setup. Please try again.");
                    return null;
                }
                return stripe
                    .confirmCardSetup(intentResp.data.client_secret, {
                        payment_method: { card: number },
                    })
                    .then((result: any) => {
                        if (result.error) {
                            fail(result.error.message || "Your card was declined.");
                            return null;
                        }
                        return postJSON(confirmUrl, {
                            setup_intent_id: result.setupIntent.id,
                        }).then((confirmResp) => {
                            if (!confirmResp.data.ok || !confirmResp.data.next) {
                                fail(
                                    "We saved your card but could not start the trial. Please reload and continue.",
                                );
                                return null;
                            }
                            window.location.href = confirmResp.data.next;
                            return true;
                        });
                    });
            })
            .catch(() => {
                fail("Something went wrong. Please try again.");
            });
    });
});
