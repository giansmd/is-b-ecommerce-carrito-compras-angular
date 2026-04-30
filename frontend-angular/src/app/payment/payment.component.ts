import { Component, OnInit } from "@angular/core";
import { Router } from "@angular/router";
import { StripeService } from "../services/stripe.service";

interface CartItem {
  productId: number;
  name: string;
  unitPrice: number;
  quantity: number;
  maxStock: number;
}

@Component({
  selector: "app-payment",
  templateUrl: "./payment.component.html",
  styleUrls: ["./payment.component.css"],
})
export class PaymentComponent implements OnInit {
  cart: CartItem[] = [];
  total = 0;
  loading = false;
  message = "";

  constructor(
    private router: Router,
    private stripe: StripeService,
  ) {}

  ngOnInit(): void {
    // Try to read cart from navigation state or history state
    const nav = this.router.getCurrentNavigation();
    const stateCart =
      (nav && (nav.extras as any)?.state && (nav.extras as any).state.cart) ||
      (history.state && (history.state as any).cart);
    this.cart = stateCart ?? [];
    this.computeTotal();
  }

  private computeTotal(): void {
    this.total = this.cart.reduce(
      (sum, item) => sum + item.unitPrice * item.quantity,
      0,
    );
  }

  payWithStripe(): void {
    if (!this.cart || this.cart.length === 0) {
      alert("El carrito está vacío");
      return;
    }
    this.loading = true;
    const payload = {
      items: this.cart.map((i) => ({
        product_id: i.productId,
        quantity: i.quantity,
      })),
    };
    this.stripe.createCheckoutSession(payload).subscribe({
      next: (res) => {
        this.loading = false;
        const url = res?.checkout_url || res?.url || res?.checkoutUrl;
        if (url) {
          // Redirect to Stripe hosted checkout (backend should return an URL)
          window.location.href = url;
        } else if (res?.sessionId) {
          // If backend returns a sessionId, redirect pattern may vary; open Stripe checkout via backend route
          window.location.href = `${this.stripe.backendBaseUrl}/stripe/checkout/${res.sessionId}`;
        } else {
          this.message = "No se recibió URL de pago desde el backend.";
        }
      },
      error: () => {
        this.loading = false;
        this.message = "Error al crear la sesión de pago.";
      },
    });
  }

  backToStore(): void {
    this.router.navigateByUrl("/");
  }
}
