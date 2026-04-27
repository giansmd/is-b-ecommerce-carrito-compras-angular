import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { AuthService } from "./auth.service";

@Injectable({ providedIn: "root" })
export class CartService {
  constructor(private http: HttpClient, private auth: AuthService) {}

  addToCart(productId: number, quantity: number): Observable<{ message: string; cart_id: number }> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    const user_id = session?.userId ?? 0;
    return this.http.post<{ message: string; cart_id: number }>(
      `${this.auth.backendUrl}/api/cart/add`,
      { user_id, product_id: productId, quantity },
      { headers },
    );
  }

  checkout(): Observable<{ order_id: number; total: number; message: string }> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    const user_id = session?.userId ?? 0;
    return this.http.post<{ order_id: number; total: number; message: string }>(
      `${this.auth.backendUrl}/api/cart/checkout`,
      { user_id },
      { headers },
    );
  }

  generateOperationalReport(startDate: string, endDate: string): Observable<{ pdf_url: string }> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.post<{ pdf_url: string }>(
      `${this.auth.backendUrl}/api/reports/operational`,
      { start_date: startDate, end_date: endDate },
      { headers },
    );
  }

  generateManagementReport(): Observable<{ pdf_url: string }> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.post<{ pdf_url: string }>(`${this.auth.backendUrl}/api/reports/management`, {}, { headers });
  }
}
