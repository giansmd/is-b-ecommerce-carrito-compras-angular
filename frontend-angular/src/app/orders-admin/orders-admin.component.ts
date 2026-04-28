import { Component, OnInit } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService } from "../services/auth.service";
import { AdminOrderDetail, AdminOrderListItem, OrderService } from "../services/order.service";

@Component({
  selector: "app-orders-admin",
  templateUrl: "./orders-admin.component.html",
  styleUrls: ["./orders-admin.component.css"],
})
export class OrdersAdminComponent implements OnInit {
  orders: AdminOrderListItem[] = [];
  selectedOrder: AdminOrderDetail | null = null;
  isLoadingOrders = false;
  isLoadingDetail = false;
  selectedOrderId: number | null = null;

  constructor(
    private orderService: OrderService,
    private auth: AuthService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    const session = this.auth.session;
    if (!session) {
      alert("Debes iniciar sesión para ver pedidos.");
      this.router.navigateByUrl("/");
      return;
    }
    if (session.role !== "admin") {
      alert("Solo un administrador puede acceder a esta pantalla.");
      this.router.navigateByUrl("/");
      return;
    }
    this.loadOrders();
  }

  loadOrders(): void {
    this.isLoadingOrders = true;
    this.orderService.listAdminOrders().subscribe({
      next: (orders) => {
        this.orders = orders;
        this.isLoadingOrders = false;
      },
      error: () => {
        this.isLoadingOrders = false;
        alert("No se pudo cargar la lista de pedidos.");
      },
    });
  }

  openDetail(orderId: number): void {
    this.selectedOrderId = orderId;
    this.isLoadingDetail = true;
    this.orderService.getAdminOrderDetail(orderId).subscribe({
      next: (detail) => {
        this.selectedOrder = detail;
        this.isLoadingDetail = false;
      },
      error: () => {
        this.isLoadingDetail = false;
        alert("No se pudo cargar el detalle del pedido.");
      },
    });
  }

  backToStore(): void {
    this.router.navigateByUrl("/");
  }

  getOrderTotal(order: AdminOrderListItem): number {
    return Number(order.total_amount) || 0;
  }

  getOrderDate(order: AdminOrderListItem): string {
    return new Date(order.order_date).toLocaleString();
  }

  getDetailTotal(): number {
    return this.selectedOrder ? Number(this.selectedOrder.total_amount) || 0 : 0;
  }

  getItemSubtotal(item: { subtotal: string | number }): number {
    return Number(item.subtotal) || 0;
  }
}
