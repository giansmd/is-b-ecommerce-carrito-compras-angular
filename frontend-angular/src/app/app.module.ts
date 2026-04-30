import { NgModule } from "@angular/core";
import { BrowserModule } from "@angular/platform-browser";
import { HttpClientModule } from "@angular/common/http";
import { FormsModule } from "@angular/forms";

import { AppRoutingModule } from "./app-routing.module";
import { AppComponent } from "./app.component";
import { OrdersAdminComponent } from "./orders-admin/orders-admin.component";
import { StoreComponent } from "./store/store.component";
import { PaymentComponent } from "./payment/payment.component";

@NgModule({
  declarations: [
    AppComponent,
    StoreComponent,
    OrdersAdminComponent,
    PaymentComponent,
  ],
  imports: [BrowserModule, AppRoutingModule, HttpClientModule, FormsModule],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
