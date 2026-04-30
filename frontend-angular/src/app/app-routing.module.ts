import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { OrdersAdminComponent } from "./orders-admin/orders-admin.component";
import { StoreComponent } from "./store/store.component";
import { PaymentComponent } from "./payment/payment.component";

const routes: Routes = [
  { path: "", component: StoreComponent },
  { path: "payment", component: PaymentComponent },
  { path: "admin/pedidos", component: OrdersAdminComponent },
  { path: "**", redirectTo: "" },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
