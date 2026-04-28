import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { AuthService } from "./auth.service";

export interface AdminOrderListItem {
  id: number;
  user_id: number;
  customer_email: string;
  total_amount: string | number;
  status: string;
  order_date: string;
  items_count: number;
}

export interface AdminOrderDetailItem {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  price: string | number;
  subtotal: string | number;
}

export interface AdminOrderDetail {
  id: number;
  user_id: number;
  customer_email: string;
  total_amount: string | number;
  status: string;
  order_date: string;
  items: AdminOrderDetailItem[];
}

@Injectable({ providedIn: "root" })
export class OrderService {
  constructor(
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  listAdminOrders(): Observable<AdminOrderListItem[]> {
    return this.http.get<AdminOrderListItem[]>(`${this.auth.backendUrl}/api/orders/admin`, {
      headers: this.authHeaders,
    });
  }

  getAdminOrderDetail(orderId: number): Observable<AdminOrderDetail> {
    return this.http.get<AdminOrderDetail>(`${this.auth.backendUrl}/api/orders/admin/${orderId}`, {
      headers: this.authHeaders,
    });
  }

  private get authHeaders(): HttpHeaders | undefined {
    const session = this.auth.session;
    return session ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`) : undefined;
  }
}
